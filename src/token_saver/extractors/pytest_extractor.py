import re

from token_saver.extractors import ExtractionResult

_SUMMARY_RE = re.compile(r"^=+ (.+) in [\d.]+s(?: \(\d+:\d{2}:\d{2}\))? ?=*$", re.MULTILINE)
_ISSUES_HEADER_RE = re.compile(r"^=+ (?:FAILURES|ERRORS) =+$", re.MULTILINE)
_SECTION_HEADER_RE = re.compile(r"^=+ .+ =+$", re.MULTILINE)
_COUNT_RE = re.compile(r"(\d+) (\w+)")


def extract_pytest(raw_output: str) -> ExtractionResult:
    summary_matches = list(_SUMMARY_RE.finditer(raw_output))
    if not summary_matches:
        return ExtractionResult(text=raw_output.strip(), metadata={"parsed": False})

    summary_line = summary_matches[-1].group(1)
    counts = {name: int(n) for n, name in _COUNT_RE.findall(summary_line)}

    issues_blocks = []
    for header in _ISSUES_HEADER_RE.finditer(raw_output):
        rest = raw_output[header.end():]
        next_header = _SECTION_HEADER_RE.search(rest)
        end = next_header.start() if next_header else len(rest)
        block = rest[:end].strip("\n")
        if block:
            issues_blocks.append(block)

    parts = [f"Resumo: {summary_line}"]
    for block in issues_blocks:
        parts.append("")
        parts.append(block)

    return ExtractionResult(
        text="\n".join(parts),
        metadata={"parsed": True, "counts": counts},
    )
