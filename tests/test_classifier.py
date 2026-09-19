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
        ("npx jest src/ 2>&1 | tail -40", CommandType.JEST),
        ("jest --silent", CommandType.JEST),
        ("yarn jest", CommandType.JEST),
        ("cd app && npm test", CommandType.JEST),
        ("npm run test -- --watch=false", CommandType.JEST),
        ("npm run test:unit", CommandType.JEST),
        ("yarn test", CommandType.JEST),
        ("pnpm test", CommandType.JEST),
        ("CI=true npx jest", CommandType.JEST),
        ("timeout 300 npx jest --silent 2>&1 | tail -60", CommandType.JEST),
        ("git stash\nnpx jest src/", CommandType.JEST),
        ("npx vitest run", CommandType.UNKNOWN),
        ("cat jest.config.js", CommandType.UNKNOWN),
        ("npm install jest", CommandType.UNKNOWN),
        ("npm run build", CommandType.UNKNOWN),
        ("ls -la", CommandType.UNKNOWN),
        ("cat /home/user/pytest/README.md", CommandType.UNKNOWN),
        ("pytest_output.log", CommandType.UNKNOWN),
        # Heuristic limitation: regex-based classifier cannot distinguish "git diff" as a real command from "git diff" inside a quoted string; this is out of scope for this lightweight component
        ("echo 'running git diff now'", CommandType.GIT_DIFF),
    ],
)
def test_classify_command(command, expected):
    assert classify_command(command) == expected
