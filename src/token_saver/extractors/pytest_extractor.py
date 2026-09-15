import re

from token_saver.extractors import ExtractionResult

_SUMMARY_RE = re.compile(r"^=+ (.+) in [\d.]+s ?=*$", re.MULTILINE)
_ISSUES_HEADER_RE = re.compile(r"^=+ (?:FAILURES|ERRORS) =+$", re.MULTILINE)
_SECTION_HEADER_RE = re.compile(r"^=+ .+ =+$", re.MULTILINE)
_COUNT_RE = re.compile(r"(\d+) (\w+)")


def extract_pytest(raw_output: str) -> ExtractionResult:
    summary_matches = list(_SUMMARY_RE.finditer(raw_output))
    if not summary_matches:
        return ExtractionResult(text=raw_output.strip(), metadata={"parsed": False})

    summary_line = summary_matches[-1].group(1)
    counts = {name: int(n) for n, name in _COUNT_RE.findall(summary_line)}

    issues_block = ""
    issues_header = _ISSUES_HEADER_RE.search(raw_output)
    if issues_header:
        rest = raw_output[issues_header.end():]
        next_header = _SECTION_HEADER_RE.search(rest)
        end = next_header.start() if next_header else len(rest)
        issues_block = rest[:end].strip("\n")

    parts = [f"Resumo: {summary_line}"]
    if issues_block:
        parts.append("")
        parts.append(issues_block)

    return ExtractionResult(
        text="\n".join(parts),
        metadata={"parsed": True, "counts": counts},
    )
