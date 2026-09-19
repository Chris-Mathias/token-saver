import re

from token_saver.extractors import ExtractionResult

_TESTS_SUMMARY_RE = re.compile(r"^Tests:\s+(.+?)\s*$", re.MULTILINE)
_SUITES_SUMMARY_RE = re.compile(r"^Test Suites:\s+(.+?)\s*$", re.MULTILINE)
_COUNT_RE = re.compile(r"(\d+) (\w+)")
_SUITE_HEADER_RE = re.compile(r"^(?:PASS|FAIL) ")
_FAILURE_BLOCK_RE = re.compile(r"^\s+● ")
_NODE_MODULES_FRAME_RE = re.compile(r"^\s+at .*node_modules/")
# With many suites Jest reprints every failure block after this line.
_REPEATED_SUMMARY = "Summary of all failing tests"


def _counts(summary: str) -> dict[str, int]:
    return {name: int(n) for n, name in _COUNT_RE.findall(summary)}


def _failure_lines(raw_output: str) -> list[str]:
    kept: list[str] = []
    in_failure_block = False
    for line in raw_output.splitlines():
        if line.startswith(_REPEATED_SUMMARY) or line.startswith("Test Suites:"):
            break
        if _SUITE_HEADER_RE.match(line):
            in_failure_block = False
            if line.startswith("FAIL "):
                kept.append(line)
        elif _FAILURE_BLOCK_RE.match(line):
            in_failure_block = True
            kept.append(line)
        elif in_failure_block and not _NODE_MODULES_FRAME_RE.match(line):
            kept.append(line)
    return kept


def _squeeze_blank_lines(lines: list[str]) -> str:
    result: list[str] = []
    for line in lines:
        if not line.strip() and (not result or not result[-1].strip()):
            continue
        result.append(line)
    return "\n".join(result).strip("\n")


def extract_jest(raw_output: str) -> ExtractionResult:
    tests_matches = _TESTS_SUMMARY_RE.findall(raw_output)
    if not tests_matches:
        return ExtractionResult(text=raw_output.strip(), metadata={"parsed": False})

    tests_summary = tests_matches[-1]
    suites_matches = _SUITES_SUMMARY_RE.findall(raw_output)
    suites_summary = suites_matches[-1] if suites_matches else ""

    header = f"Resumo: {tests_summary}"
    if suites_summary:
        header += f" (suítes: {suites_summary})"

    body = _squeeze_blank_lines(_failure_lines(raw_output))
    text = f"{header}\n\n{body}" if body else header

    return ExtractionResult(
        text=text,
        metadata={
            "parsed": True,
            "counts": _counts(tests_summary),
            "suite_counts": _counts(suites_summary),
        },
    )
