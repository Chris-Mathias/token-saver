#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from token_saver.classifier import CommandType, classify_command, describe_command_shape
from token_saver.extractors import ExtractionResult
from token_saver.extractors.django_test_extractor import extract_django_test
from token_saver.extractors.git_diff_extractor import extract_git_diff
from token_saver.extractors.jest_extractor import extract_jest
from token_saver.extractors.vitest_extractor import extract_vitest
from token_saver.extractors.pytest_extractor import extract_pytest
from token_saver.logger import EventRecord, log_event
from token_saver.tokenizer import count_tokens
from token_saver.truncate import paired_truncate

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "events.jsonl"
_EXIT_CODE_RE = re.compile(r"^Exit code (\d+)\n?")


def resolve_data_path() -> Path:
    # Each collection target writes to its own file, so a coleta's dataset
    # never mixes with events from developing the prototype itself.
    configured = os.environ.get("TOKEN_SAVER_DATA_PATH")
    return Path(configured) if configured else DATA_PATH


def _extract_output_text(tool_response) -> str:
    if isinstance(tool_response, str):
        return tool_response
    if isinstance(tool_response, dict):
        if "text" in tool_response:
            return tool_response["text"]
        parts = [tool_response.get("stdout", ""), tool_response.get("stderr", "")]
        return "\n".join(p for p in parts if p)
    return ""


def _split_failure_error(error: str) -> tuple[str, int | None]:
    # PostToolUseFailure puts the output in `error`, prefixed by an "Exit code N"
    # line; without that line the shell never ran and there is no exit code.
    match = _EXIT_CODE_RE.match(error)
    if not match:
        return error, None
    return error[match.end():], int(match.group(1))


def _extract_node_test(raw_output: str) -> ExtractionResult:
    # `npm test` runs whatever the project configured, so the runner is
    # identified by which extractor recognizes the output.
    for runner, extract in (("vitest", extract_vitest), ("jest", extract_jest)):
        extraction = extract(raw_output)
        if extraction.metadata.get("parsed"):
            extraction.metadata["runner"] = runner
            return extraction
    return ExtractionResult(
        text=raw_output.strip(), metadata={"parsed": False, "runner": None}
    )


def _extract(command_type: CommandType, raw_output: str) -> ExtractionResult:
    # Resolved per call so the extractors stay replaceable (tests patch them).
    extractors = {
        CommandType.TEST_RUNNER: extract_pytest,
        CommandType.GIT_DIFF: extract_git_diff,
        CommandType.JEST: extract_jest,
        CommandType.VITEST: extract_vitest,
        CommandType.DJANGO_TEST: extract_django_test,
        CommandType.NODE_TEST: _extract_node_test,
    }
    return extractors[command_type](raw_output)


def process_event(payload: dict, data_path: Path) -> None:
    if payload.get("tool_name") != "Bash":
        return

    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "")
    if not command:
        return

    command_type = classify_command(command)
    if command_type is CommandType.UNKNOWN:
        return

    if payload.get("hook_event_name") == "PostToolUseFailure":
        raw_output, exit_code = _split_failure_error(payload.get("error") or "")
    else:
        raw_output = _extract_output_text(payload.get("tool_response"))
        exit_code = 0

    extractor_error = None
    s2b_output = ""
    s2b_metadata: dict = {}
    try:
        extraction = _extract(command_type, raw_output)
        s2b_output = extraction.text
        s2b_metadata = extraction.metadata
    except Exception as exc:  # extractor must never crash the real session
        extractor_error = str(exc)

    try:
        raw_tokens = count_tokens(raw_output)
        s2b_tokens = count_tokens(s2b_output)
        s2a_output = paired_truncate(raw_output, target_tokens=s2b_tokens) if s2b_output else ""
        s2a_tokens = count_tokens(s2a_output) if s2a_output else 0
        approx_fallback = False
    except Exception:
        # paired_truncate also calls the tokenizer internally (encode/decode), so it
        # must share this try/except rather than run after it — otherwise a tokenizer
        # failure here would propagate uncaught and violate "never crash the real session".
        raw_tokens = len(raw_output) // 4
        s2b_tokens = len(s2b_output) // 4
        s2a_output = ""
        s2a_tokens = 0
        approx_fallback = True

    event = EventRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        command=command,
        command_type=command_type.value,
        raw_output=raw_output,
        raw_tokens=raw_tokens,
        s2a_output=s2a_output,
        s2a_tokens=s2a_tokens,
        s2b_output=s2b_output,
        s2b_tokens=s2b_tokens,
        s2b_metadata=s2b_metadata,
        extractor_error=extractor_error,
        approx_fallback=approx_fallback,
        exit_code=exit_code,
        session_id=payload.get("session_id"),
        transcript_path=payload.get("transcript_path"),
        cwd=payload.get("cwd"),
        tool_use_id=payload.get("tool_use_id"),
        **describe_command_shape(command),
    )
    log_event(event, data_path)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    try:
        process_event(payload, resolve_data_path())
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
