import re
from enum import Enum


class CommandType(Enum):
    TEST_RUNNER = "test_runner"
    GIT_DIFF = "git_diff"
    UNKNOWN = "unknown"


_TEST_RUNNER_RE = re.compile(r"(?:^|[\s;&|])(?:python3?\s+-m\s+)?pytest(?:\s|$)")
_GIT_DIFF_RE = re.compile(r"(?:^|[\s;&|])git\s+diff(?:\s|$)")


def classify_command(command: str) -> CommandType:
    if _TEST_RUNNER_RE.search(command):
        return CommandType.TEST_RUNNER
    if _GIT_DIFF_RE.search(command):
        return CommandType.GIT_DIFF
    return CommandType.UNKNOWN
