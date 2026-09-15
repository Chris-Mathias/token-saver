import json

from token_saver.logger import EventRecord, log_event


def _sample_event(**overrides) -> EventRecord:
    defaults = dict(
        timestamp="2026-09-14T12:00:00Z",
        command="pytest",
        command_type="test_runner",
        raw_output="raw",
        raw_tokens=10,
        s2a_output="trunc",
        s2a_tokens=5,
        s2b_output="extracted",
        s2b_tokens=5,
    )
    defaults.update(overrides)
    return EventRecord(**defaults)


def test_log_event_appends_json_line(tmp_path):
    path = tmp_path / "events.jsonl"
    log_event(_sample_event(), path)
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["command"] == "pytest"
    assert record["command_type"] == "test_runner"
    assert record["extractor_error"] is None


def test_log_event_appends_multiple_events(tmp_path):
    path = tmp_path / "events.jsonl"
    for i in range(3):
        log_event(_sample_event(command="git diff", command_type="git_diff"), path)
    lines = path.read_text().splitlines()
    assert len(lines) == 3


def test_log_event_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "events.jsonl"
    log_event(_sample_event(extractor_error="boom"), path)
    record = json.loads(path.read_text().splitlines()[0])
    assert record["extractor_error"] == "boom"
