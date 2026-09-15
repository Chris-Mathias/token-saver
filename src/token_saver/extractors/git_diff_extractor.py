import re

from token_saver.extractors import ExtractionResult

_HUNK_HEADER_RE = re.compile(r"^@@ .+ @@.*$")


def _collapse_context_runs(
    body_lines: list[str], context_lines: int
) -> tuple[list[str], int]:
    result: list[str] = []
    collapses = 0
    i = 0
    n = len(body_lines)
    while i < n:
        line = body_lines[i]
        if line.startswith(" "):
            j = i
            while j < n and body_lines[j].startswith(" "):
                j += 1
            run = body_lines[i:j]
            if len(run) > 2 * context_lines:
                omitted = len(run) - 2 * context_lines
                result.extend(run[:context_lines])
                result.append(f"... {omitted} linhas inalteradas omitidas ...")
                result.extend(run[-context_lines:] if context_lines else [])
                collapses += 1
            else:
                result.extend(run)
            i = j
        else:
            result.append(line)
            i += 1
    return result, collapses


def extract_git_diff(raw_output: str, context_lines: int = 1) -> ExtractionResult:
    lines = raw_output.splitlines()
    output_lines: list[str] = []
    current_hunk_body: list[str] = []
    in_hunk = False
    hunk_count = 0
    total_collapses = 0

    def close_hunk() -> None:
        nonlocal total_collapses
        if current_hunk_body:
            processed, collapses = _collapse_context_runs(current_hunk_body, context_lines)
            output_lines.extend(processed)
            total_collapses += collapses
            current_hunk_body.clear()

    for line in lines:
        if _HUNK_HEADER_RE.match(line):
            close_hunk()
            output_lines.append(line)
            in_hunk = True
            hunk_count += 1
        elif in_hunk and (line.startswith("+") or line.startswith("-") or line.startswith(" ")):
            current_hunk_body.append(line)
        else:
            close_hunk()
            in_hunk = False
            output_lines.append(line)

    close_hunk()

    return ExtractionResult(
        text="\n".join(output_lines),
        metadata={"hunks": hunk_count, "context_blocks_collapsed": total_collapses},
    )
