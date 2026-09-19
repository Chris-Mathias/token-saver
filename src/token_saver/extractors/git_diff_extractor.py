import re

from token_saver.extractors import ExtractionResult

_HUNK_HEADER_RE = re.compile(r"^@@ .+ @@.*$")
_FILE_HEADER_RE = re.compile(r"^diff --git ")
_INDEX_RE = re.compile(r"^index [0-9a-f]+\.\.[0-9a-f]+")
# A marker costs ~11 tokens and a context line ~8, so collapsing fewer than two
# lines would make the output larger, not smaller.
_MIN_OMITTED_LINES = 2


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
            omitted = len(run) - 2 * context_lines
            if omitted >= _MIN_OMITTED_LINES:
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


def _file_header_names_file(header: list[str]) -> bool:
    return any(
        line.startswith(("+++ ", "Binary files ", "rename to ")) for line in header
    )


def _drop_redundant_header_lines(lines: list[str]) -> tuple[list[str], int]:
    # `diff --git` repeats the paths already in `---`/`+++`, and `index` only
    # carries blob hashes; both go, unless `diff --git` is the only line naming
    # the file (e.g. a mode-only change).
    result: list[str] = []
    removed = 0
    in_header = False
    for i, line in enumerate(lines):
        if _FILE_HEADER_RE.match(line):
            in_header = True
            header_end = next(
                (k for k in range(i + 1, len(lines))
                 if _HUNK_HEADER_RE.match(lines[k]) or _FILE_HEADER_RE.match(lines[k])),
                len(lines),
            )
            if _file_header_names_file(lines[i + 1:header_end]):
                removed += 1
                continue
        elif _HUNK_HEADER_RE.match(line):
            in_header = False
        elif in_header and _INDEX_RE.match(line):
            removed += 1
            continue
        result.append(line)
    return result, removed


def extract_git_diff(raw_output: str, context_lines: int = 0) -> ExtractionResult:
    lines, header_lines_removed = _drop_redundant_header_lines(raw_output.splitlines())
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
        metadata={
            "hunks": hunk_count,
            "context_blocks_collapsed": total_collapses,
            "header_lines_removed": header_lines_removed,
        },
    )
