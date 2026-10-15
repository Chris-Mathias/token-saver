import pytest

from token_saver.classifier import CommandType, classify_command, describe_command_shape


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
        ("cd app && npm test", CommandType.NODE_TEST),
        ("npm run test -- --watch=false", CommandType.NODE_TEST),
        ("npm run test:unit", CommandType.NODE_TEST),
        ("yarn test", CommandType.NODE_TEST),
        ("pnpm test", CommandType.NODE_TEST),
        ("CI=true npx jest", CommandType.JEST),
        ("timeout 300 npx jest --silent 2>&1 | tail -60", CommandType.JEST),
        ("git stash\nnpx jest src/", CommandType.JEST),
        ("npx vitest run", CommandType.VITEST),
        ("vitest run src/display-input 2>&1 | tail -50", CommandType.VITEST),
        ("timeout 60 npx vitest run --config ./vitest.config.e2e.ts x", CommandType.VITEST),
        ("python manage.py test", CommandType.DJANGO_TEST),
        ("cd iecb_api && .venv/bin/python manage.py test shop", CommandType.DJANGO_TEST),
        ("coverage run manage.py test", CommandType.DJANGO_TEST),
        ("./manage.py test --keepdb", CommandType.DJANGO_TEST),
        ("python manage.py migrate", CommandType.UNKNOWN),
        ("cat manage.py", CommandType.UNKNOWN),
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


@pytest.mark.parametrize(
    "command,expected",
    [
        ("npx vitest run", {"command_segments": 1, "has_heredoc": False, "truncating_pipe": False}),
        ("npx vitest run 2>&1 | tail -50", {"command_segments": 1, "has_heredoc": False, "truncating_pipe": True}),
        ("cd app && npm test", {"command_segments": 2, "has_heredoc": False, "truncating_pipe": False}),
        ("git stash\nnpx jest", {"command_segments": 2, "has_heredoc": False, "truncating_pipe": False}),
        ("python3 - <<'EOF'\nprint(1)\nEOF\npython manage.py test", {"command_segments": 2, "has_heredoc": True, "truncating_pipe": False}),
        ("npm test | grep -c PASS", {"command_segments": 1, "has_heredoc": False, "truncating_pipe": True}),
        ("npm test | cat", {"command_segments": 1, "has_heredoc": False, "truncating_pipe": False}),
    ],
)
def test_describe_command_shape(command, expected):
    assert describe_command_shape(command) == expected
