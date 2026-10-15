import re

from token_saver.extractors import ExtractionResult

_TESTS_SUMMARY_RE = re.compile(r"^\s*Tests\s+(.+?)\s*$", re.MULTILINE)
_FILES_SUMMARY_RE = re.compile(r"^\s*Test Files\s+(.+?)\s*$", re.MULTILINE)
_COUNT_RE = re.compile(r"(\d+) (\w+)")
_TOTAL_RE = re.compile(r"\((\d+)\)\s*$")
# Vitest groups failures under banners drawn with U+23AF, and separates each
# block with a line of the same character; the banners mark where the useful
# part of the output starts.
_FAILED_BANNER_RE = re.compile(r"^⎯+ Failed (?:Tests|Suites) \d+ ⎯+$")
_SEPARATOR_RE = re.compile(r"^⎯+(?:\[\d+/\d+\])?⎯*$")


def _counts(summary: str) -> dict[str, int]:
    counts = {name: int(n) for n, name in _COUNT_RE.findall(summary)}
    total = _TOTAL_RE.search(summary)
    if total:
        counts["total"] = int(total.group(1))
    return counts


def _failure_lines(raw_output: str) -> list[str]:
    kept: list[str] = []
    collecting = False
    for line in raw_output.splitlines():
        if _FAILED_BANNER_RE.match(line.strip()):
            collecting = True
            continue
        if _FILES_SUMMARY_RE.match(line):
            break
        if collecting and not _SEPARATOR_RE.match(line.strip()):
            kept.append(line)
    return kept


def _squeeze_blank_lines(lines: list[str]) -> str:
    result: list[str] = []
    for line in lines:
        if not line.strip() and (not result or not result[-1].strip()):
            continue
        result.append(line)
    return "\n".join(result).strip("\n")


def extract_vitest(raw_output: str) -> ExtractionResult:
    tests_matches = _TESTS_SUMMARY_RE.findall(raw_output)
    if not tests_matches:
        return ExtractionResult(text=raw_output.strip(), metadata={"parsed": False})

    tests_summary = tests_matches[-1]
    files_matches = _FILES_SUMMARY_RE.findall(raw_output)
    files_summary = files_matches[-1] if files_matches else ""

    header = f"Resumo: {tests_summary}"
    if files_summary:
        header += f" (arquivos: {files_summary})"

    body = _squeeze_blank_lines(_failure_lines(raw_output))
    text = f"{header}\n\n{body}" if body else header

    return ExtractionResult(
        text=text,
        metadata={
            "parsed": True,
            "counts": _counts(tests_summary),
            "file_counts": _counts(files_summary),
        },
    )
