import json

from hooks.post_tool_use import process_event


def test_process_event_logs_pytest_event(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_response": {"type": "text", "text": "===== 2 passed in 0.01s ====="},
    }
    process_event(payload, data_path)
    lines = data_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["command_type"] == "test_runner"
    assert record["s2b_tokens"] > 0
    assert record["extractor_error"] is None


def test_process_event_ignores_non_bash_tool(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {"tool_name": "Read", "tool_input": {}, "tool_response": {}}
    process_event(payload, data_path)
    assert not data_path.exists()


def test_process_event_ignores_unknown_command(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "tool_response": {"type": "text", "text": "file1\nfile2"},
    }
    process_event(payload, data_path)
    assert not data_path.exists()


def test_process_event_logs_git_diff_event_with_string_tool_response(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git diff"},
        "tool_response": "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-old\n+new\n",
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["command_type"] == "git_diff"
    assert "new" in record["s2b_output"]


def test_process_event_logs_extractor_error_without_raising(tmp_path, monkeypatch):
    data_path = tmp_path / "events.jsonl"

    def _raise(*args, **kwargs):
        raise ValueError("parse failed")

    monkeypatch.setattr("hooks.post_tool_use.extract_pytest", _raise)
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest"},
        "tool_response": {"type": "text", "text": "garbage"},
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["extractor_error"] == "parse failed"
    assert record["s2b_output"] == ""


def test_process_event_tokenizer_failure_falls_back_without_raising(tmp_path, monkeypatch):
    data_path = tmp_path / "events.jsonl"

    def _raise(*args, **kwargs):
        raise RuntimeError("tokenizer unavailable")

    monkeypatch.setattr("hooks.post_tool_use.count_tokens", _raise)
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git diff"},
        "tool_response": "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-old\n+new\n",
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["approx_fallback"] is True
    assert record["s2a_output"] == ""
    assert record["s2a_tokens"] == 0
