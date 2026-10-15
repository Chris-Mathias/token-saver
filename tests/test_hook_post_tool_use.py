import io
import json
from pathlib import Path

from hooks.post_tool_use import main, process_event, resolve_data_path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
    assert record["s2b_metadata"]["counts"] == {"passed": 2}


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
    assert record["s2b_metadata"]["hunks"] == 1


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


def test_main_returns_0_even_when_process_event_raises(monkeypatch):
    payload = {"tool_name": "Bash", "tool_input": "not a dict", "tool_response": {}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    result = main()
    assert result == 0


def test_process_event_logs_failed_pytest_from_post_tool_use_failure(tmp_path):
    data_path = tmp_path / "events.jsonl"
    output = (FIXTURES_DIR / "pytest_output" / "with_failures.txt").read_text()
    payload = {
        "hook_event_name": "PostToolUseFailure",
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "error": f"Exit code 1\n{output}",
        "is_interrupt": False,
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert not record["raw_output"].startswith("Exit code")
    assert record["exit_code"] == 1
    assert record["s2b_metadata"]["counts"] == {"failed": 1, "passed": 2}
    assert "tests/test_math.py:5: AssertionError" in record["s2b_output"]


def test_process_event_failure_without_exit_code_line(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "hook_event_name": "PostToolUseFailure",
        "tool_name": "Bash",
        "tool_input": {"command": "pytest"},
        "error": "spawn /bin/zsh ENOENT",
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["exit_code"] is None
    assert record["raw_output"] == "spawn /bin/zsh ENOENT"


def test_process_event_successful_call_records_exit_code_zero(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "pytest"},
        "tool_response": {"stdout": "===== 2 passed in 0.01s =====", "stderr": ""},
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["exit_code"] == 0


def test_process_event_logs_jest_event(tmp_path):
    data_path = tmp_path / "events.jsonl"
    output = (FIXTURES_DIR / "jest_output" / "with_failures.txt").read_text()
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "npx jest 2>&1 | tail -80"},
        "tool_response": {"stdout": output, "stderr": ""},
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["command_type"] == "jest"
    assert record["s2b_metadata"]["counts"] == {"failed": 2, "passed": 1, "total": 3}
    assert record["s2b_tokens"] < record["raw_tokens"]


def test_process_event_records_session_context_for_later_linking(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "abc123",
        "transcript_path": "/home/user/.claude/projects/-x/abc123.jsonl",
        "cwd": "/home/user/project/sub",
        "tool_use_id": "toolu_01ABC",
        "tool_name": "Bash",
        "tool_input": {"command": "pytest"},
        "tool_response": {"stdout": "===== 2 passed in 0.01s ====="},
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["session_id"] == "abc123"
    assert record["transcript_path"] == "/home/user/.claude/projects/-x/abc123.jsonl"
    assert record["cwd"] == "/home/user/project/sub"
    assert record["tool_use_id"] == "toolu_01ABC"


def test_process_event_without_session_context_keeps_fields_empty(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest"},
        "tool_response": {"stdout": "===== 2 passed in 0.01s ====="},
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["session_id"] is None
    assert record["tool_use_id"] is None


def test_process_event_logs_django_test_event(tmp_path):
    data_path = tmp_path / "events.jsonl"
    output = (FIXTURES_DIR / "django_test_output" / "with_failures.txt").read_text()
    payload = {
        "hook_event_name": "PostToolUseFailure",
        "tool_name": "Bash",
        "tool_input": {"command": "python manage.py test"},
        "error": f"Exit code 1\n{output}",
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["command_type"] == "django_test"
    assert record["s2b_metadata"]["counts"] == {"total": 3, "failures": 1}
    assert record["s2b_tokens"] < record["raw_tokens"]


def test_process_event_logs_vitest_event(tmp_path):
    data_path = tmp_path / "events.jsonl"
    output = (FIXTURES_DIR / "vitest_output" / "with_failures.txt").read_text()
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "npx vitest run src/"},
        "tool_response": {"stdout": output},
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["command_type"] == "vitest"
    assert record["s2b_metadata"]["counts"]["failed"] == 2


def test_process_event_npm_test_picks_runner_from_output(tmp_path):
    data_path = tmp_path / "events.jsonl"
    vitest_output = (FIXTURES_DIR / "vitest_output" / "with_failures.txt").read_text()
    jest_output = (FIXTURES_DIR / "jest_output" / "with_failures.txt").read_text()
    for output in (vitest_output, jest_output):
        process_event(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "npm test"},
                "tool_response": {"stdout": output},
            },
            data_path,
        )
    records = [json.loads(line) for line in data_path.read_text().splitlines()]
    assert [r["command_type"] for r in records] == ["node_test", "node_test"]
    assert [r["s2b_metadata"]["runner"] for r in records] == ["vitest", "jest"]
    assert all(r["s2b_metadata"]["parsed"] for r in records)


def test_process_event_npm_test_with_unknown_runner(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "npm test"},
        "tool_response": {"stdout": "1..2\nok 1 - soma\nok 2 - texto\n"},
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["s2b_metadata"]["parsed"] is False


def test_resolve_data_path_defaults_to_project_data_dir(monkeypatch):
    monkeypatch.delenv("TOKEN_SAVER_DATA_PATH", raising=False)
    path = resolve_data_path()
    assert path.name == "events.jsonl"
    assert path.parent.name == "data"


def test_resolve_data_path_honours_env_var(monkeypatch, tmp_path):
    target = tmp_path / "coleta" / "site-iecb.jsonl"
    monkeypatch.setenv("TOKEN_SAVER_DATA_PATH", str(target))
    assert resolve_data_path() == target


def test_process_event_records_command_shape(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "python3 - <<'EOF'\nprint(1)\nEOF\ncd app && npm test 2>&1 | tail -20"},
        "tool_response": {"stdout": "Tests  2 passed (2)"},
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["command_segments"] == 3
    assert record["has_heredoc"] is True
    assert record["truncating_pipe"] is True
