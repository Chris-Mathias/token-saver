import re

from token_saver.extractors import ExtractionResult

# `manage.py test` delegates to unittest, so the summary is unittest's: a
# "Ran N tests" line followed by OK or FAILED with the per-kind counts.
_RAN_RE = re.compile(r"^Ran (\d+) tests? in [\d.]+s$", re.MULTILINE)
_STATUS_RE = re.compile(r"^(OK|FAILED)(?: \((.+)\))?$", re.MULTILINE)
_COUNT_RE = re.compile(r"(\w+)=(\d+)")
_ISSUE_HEADER_RE = re.compile(r"^(?:FAIL|ERROR): \S+")
_SEPARATOR_RE = re.compile(r"^(?:=+|-+)$")


def _issue_lines(raw_output: str) -> list[str]:
    kept: list[str] = []
    collecting = False
    for line in raw_output.splitlines():
        if _ISSUE_HEADER_RE.match(line):
            collecting = True
        elif _RAN_RE.match(line):
            collecting = False
        if collecting and not _SEPARATOR_RE.match(line):
            kept.append(line)
    return kept


def _squeeze_blank_lines(lines: list[str]) -> str:
    result: list[str] = []
    for line in lines:
        if not line.strip() and (not result or not result[-1].strip()):
            continue
        result.append(line)
    return "\n".join(result).strip("\n")


def extract_django_test(raw_output: str) -> ExtractionResult:
    ran = _RAN_RE.search(raw_output)
    if not ran:
        return ExtractionResult(text=raw_output.strip(), metadata={"parsed": False})

    counts = {"total": int(ran.group(1))}
    status_match = _STATUS_RE.search(raw_output, ran.end())
    status = status_match.group(1) if status_match else "?"
    detail = status_match.group(2) if status_match and status_match.group(2) else ""
    counts.update({name: int(n) for name, n in _COUNT_RE.findall(detail)})

    header = f"Resumo: {counts['total']} testes — {status}"
    if detail:
        header += f" ({detail})"

    body = _squeeze_blank_lines(_issue_lines(raw_output))
    text = f"{header}\n\n{body}" if body else header

    return ExtractionResult(
        text=text,
        metadata={"parsed": True, "ok": status == "OK", "counts": counts},
    )
