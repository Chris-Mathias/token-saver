import re
from enum import Enum


class CommandType(Enum):
    TEST_RUNNER = "test_runner"
    GIT_DIFF = "git_diff"
    JEST = "jest"
    VITEST = "vitest"
    NODE_TEST = "node_test"
    DJANGO_TEST = "django_test"
    UNKNOWN = "unknown"


_TEST_RUNNER_RE = re.compile(r"(?:^|[\s;&|])(?:python3?\s+-m\s+)?pytest(?:\s|$)")
_GIT_DIFF_RE = re.compile(r"(?:^|[\s;&|])git\s+diff(?:\s|$)")
# Anchored to command position (optionally after env assignments) so that
# arguments such as `npm install jest` don't count as running the test suite.
_COMMAND_START = r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*(?:timeout\s+\S+\s+)?"
_JEST_RE = re.compile(
    _COMMAND_START
    + r"(?:npx\s+|yarn\s+|pnpm\s+(?:exec\s+)?|bunx\s+|\S*node_modules/\.bin/)?jest(?:\s|$)"
)
_VITEST_RE = re.compile(
    _COMMAND_START
    + r"(?:npx\s+|yarn\s+|pnpm\s+(?:exec\s+)?|bunx\s+|\S*node_modules/\.bin/)?vitest(?:\s|$)"
)
# `npm test` hides whichever runner the project configured, so the extractor is
# chosen from the output instead of from the command.
_NODE_TEST_RE = re.compile(
    _COMMAND_START + r"(?:npm|yarn|pnpm)\s+(?:run\s+)?(?:test|t)(?::\S+)?(?:\s|$)"
)
_DJANGO_TEST_RE = re.compile(r"(?:^|[\s;&|(\n])\S*manage\.py\s+test(?:\s|$)")


_HEREDOC_BODY_RE = re.compile(r"<<-?\s*(['\"]?)(\w+)\1\n.*?^\2$", re.DOTALL | re.MULTILINE)
_HEREDOC_START_RE = re.compile(r"<<-?\s*['\"]?\w+")
_SEPARATOR_RE = re.compile(r"&&|\|\||;|\n")
_TRUNCATING_PIPE_RE = re.compile(r"\|\s*(?:tail|head|grep|sed|awk|cut|wc)\b")


def describe_command_shape(command: str) -> dict:
    """Signals that tell a clean event from a compound or pre-truncated one.

    Real sessions chain editing scripts and test runs in a single call, so the
    captured output is often several programs' output concatenated — the
    analysis needs to be able to filter those out.
    """
    without_heredocs = _HEREDOC_BODY_RE.sub("", command)
    segments = [p for p in _SEPARATOR_RE.split(without_heredocs) if p.strip()]
    return {
        "command_segments": len(segments) or 1,
        "has_heredoc": bool(_HEREDOC_START_RE.search(command)),
        "truncating_pipe": bool(_TRUNCATING_PIPE_RE.search(without_heredocs)),
    }


def classify_command(command: str) -> CommandType:
    if _TEST_RUNNER_RE.search(command):
        return CommandType.TEST_RUNNER
    if _GIT_DIFF_RE.search(command):
        return CommandType.GIT_DIFF
    if _DJANGO_TEST_RE.search(command):
        return CommandType.DJANGO_TEST
    if _JEST_RE.search(command):
        return CommandType.JEST
    if _VITEST_RE.search(command):
        return CommandType.VITEST
    if _NODE_TEST_RE.search(command):
        return CommandType.NODE_TEST
    return CommandType.UNKNOWN
