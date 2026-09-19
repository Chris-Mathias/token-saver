#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from token_saver.classifier import CommandType, classify_command
from token_saver.extractors.git_diff_extractor import extract_git_diff
from token_saver.extractors.jest_extractor import extract_jest
from token_saver.extractors.pytest_extractor import extract_pytest
from token_saver.logger import EventRecord, log_event
from token_saver.tokenizer import count_tokens
from token_saver.truncate import paired_truncate

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "events.jsonl"
_EXIT_CODE_RE = re.compile(r"^Exit code (\d+)\n?")


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
        if command_type is CommandType.TEST_RUNNER:
            extraction = extract_pytest(raw_output)
            s2b_output = extraction.text
            s2b_metadata = extraction.metadata
        elif command_type is CommandType.GIT_DIFF:
            extraction = extract_git_diff(raw_output)
            s2b_output = extraction.text
            s2b_metadata = extraction.metadata
        elif command_type is CommandType.JEST:
            extraction = extract_jest(raw_output)
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
    )
    log_event(event, data_path)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    try:
        process_event(payload, DATA_PATH)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
