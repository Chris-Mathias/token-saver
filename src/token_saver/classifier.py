import re
from enum import Enum


class CommandType(Enum):
    TEST_RUNNER = "test_runner"
    GIT_DIFF = "git_diff"
    JEST = "jest"
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
# `npm test` may run another runner; the extractor then reports parsed=False.
_NPM_TEST_RE = re.compile(
    _COMMAND_START + r"(?:npm|yarn|pnpm)\s+(?:run\s+)?(?:test|t)(?::\S+)?(?:\s|$)"
)


def classify_command(command: str) -> CommandType:
    if _TEST_RUNNER_RE.search(command):
        return CommandType.TEST_RUNNER
    if _GIT_DIFF_RE.search(command):
        return CommandType.GIT_DIFF
    if _JEST_RE.search(command) or _NPM_TEST_RE.search(command):
        return CommandType.JEST
    return CommandType.UNKNOWN
