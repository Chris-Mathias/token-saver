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
