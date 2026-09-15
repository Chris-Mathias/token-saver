import pytest

from token_saver.classifier import CommandType, classify_command


@pytest.mark.parametrize(
    "command,expected",
    [
        ("pytest tests/", CommandType.TEST_RUNNER),
        ("python -m pytest -v", CommandType.TEST_RUNNER),
        ("python3 -m pytest", CommandType.TEST_RUNNER),
        ("cd repo && pytest", CommandType.TEST_RUNNER),
        ("git diff HEAD~1", CommandType.GIT_DIFF),
        ("git diff --stat", CommandType.GIT_DIFF),
        ("git diff", CommandType.GIT_DIFF),
        ("ls -la", CommandType.UNKNOWN),
        ("npm test", CommandType.UNKNOWN),
        ("cat /home/user/pytest/README.md", CommandType.UNKNOWN),
        ("pytest_output.log", CommandType.UNKNOWN),
        ("echo 'running git diff now'", CommandType.UNKNOWN),
    ],
)
def test_classify_command(command, expected):
    assert classify_command(command) == expected
