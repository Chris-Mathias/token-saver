#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from token_saver.classifier import CommandType, classify_command
from token_saver.extractors.git_diff_extractor import extract_git_diff
from token_saver.extractors.pytest_extractor import extract_pytest
from token_saver.logger import EventRecord, log_event
from token_saver.tokenizer import count_tokens
from token_saver.truncate import paired_truncate

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "events.jsonl"


def _extract_output_text(tool_response) -> str:
    if isinstance(tool_response, str):
        return tool_response
    if isinstance(tool_response, dict):
        if "text" in tool_response:
            return tool_response["text"]
        parts = [tool_response.get("stdout", ""), tool_response.get("stderr", "")]
        return "\n".join(p for p in parts if p)
    return ""


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

    raw_output = _extract_output_text(payload.get("tool_response"))

    extractor_error = None
    s2b_output = ""
    try:
        if command_type is CommandType.TEST_RUNNER:
            s2b_output = extract_pytest(raw_output).text
        elif command_type is CommandType.GIT_DIFF:
            s2b_output = extract_git_diff(raw_output).text
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
        extractor_error=extractor_error,
        approx_fallback=approx_fallback,
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
