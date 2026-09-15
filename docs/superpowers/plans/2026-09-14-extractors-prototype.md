# Token Saver — Protótipo de Extratores Determinísticos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic Token Saver prototype (Claude Code `PostToolUse` hook + classifier + pytest/`git diff` extractors + paired-truncation baseline + JSONL logger) that observes real Bash tool calls without altering the session, laying the groundwork for the later fidelity experiment.

**Architecture:** A pure-Python library (`src/token_saver/`) with one responsibility per module — classification, tokenization, extraction (one file per command type), truncation, logging — imported by a thin hook script (`hooks/post_tool_use.py`) that Claude Code invokes directly. The library has no dependency on the hook protocol, so a later phase (out of scope here) can reuse the same extractors for offline experiment replay.

**Tech Stack:** Python 3.11+, `uv` for environment/dependency management, `tiktoken` (local approximate tokenizer), `pytest` for the test suite itself.

**Spec:** `docs/superpowers/specs/2026-09-14-extractors-prototype-design.md`

## Global Constraints

- Python >= 3.11, managed via `uv` (`pyproject.toml` + `uv.lock`) — one runtime dependency (`tiktoken`), one dev dependency (`pytest`).
- Test runner covered by the extractor: **pytest only** (not Jest) — a project-scope decision, do not add Jest support.
- Token counting uses `tiktoken`'s `cl100k_base` encoding as a documented **local approximation** of Claude's real tokenizer — not exact, swap-in point for the Anthropic `count_tokens` endpoint is a later phase, not this plan.
- `data/*.jsonl` must **never** be committed to git — it may contain proprietary code from real sessions. `.gitignore` must exclude it from the first commit onward.
- The hook must **always** exit `0` in this phase — it is a pure observer (log-only mode) and must never block or alter a real tool call.
- Any exception inside an extractor must be caught inside the hook process and must never propagate to crash the user's real Claude Code session.
- The git repository at `Token-Saver/` is already initialized (branch `main`, first commit `44b4c08` containing the spec) — this plan's tasks continue from there with their own commits.
- No live Anthropic API calls, no dataset collection sessions, and no statistical analysis are part of this plan — those belong to a future spec (Fase 3+).

---

### Task 0: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/token_saver/__init__.py`
- Create: `src/token_saver/extractors/__init__.py`
- Create: `hooks/__init__.py`
- Create: `data/.gitkeep`

**Interfaces:**
- Produces: an installable `token_saver` package (editable install via `uv sync`) and an `hooks` package importable from the project root during tests.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "token-saver"
version = "0.1.0"
description = "Deterministic extractors for Claude Code Bash tool output (TCC prototype)"
requires-python = ">=3.11"
dependencies = [
    "tiktoken>=0.8.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/token_saver"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
data/*.jsonl
```

- [ ] **Step 3: Create the package skeleton (all empty files)**

Create these three empty files:
- `src/token_saver/__init__.py`
- `src/token_saver/extractors/__init__.py`
- `hooks/__init__.py`

- [ ] **Step 4: Create `data/.gitkeep`**

Empty file at `data/.gitkeep` so the directory is tracked by git while `data/*.jsonl` stays ignored.

- [ ] **Step 5: Create `README.md`**

```markdown
# Token Saver

Protótipo de extratores determinísticos para saídas de ferramentas do Claude Code (TCC — Fases 0–2 do escopo de 80h).

Ver spec completa em `docs/superpowers/specs/2026-09-14-extractors-prototype-design.md`.

## Setup

\`\`\`bash
uv sync
\`\`\`

## Rodar os testes

\`\`\`bash
uv run pytest
\`\`\`
```

- [ ] **Step 6: Sync the environment**

Run: `uv sync`
Expected: creates `.venv/` and `uv.lock`, installs `tiktoken` and `pytest`, no errors.

- [ ] **Step 7: Verify the package imports**

Run: `uv run python -c "import token_saver; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock .gitignore README.md src hooks data/.gitkeep
git commit -m "chore: scaffold token_saver package with uv"
```

---

### Task 1: `tokenizer.py`

**Files:**
- Create: `src/token_saver/tokenizer.py`
- Test: `tests/test_tokenizer.py`

**Interfaces:**
- Produces: `count_tokens(text: str) -> int`, `encode(text: str) -> list[int]`, `decode(tokens: list[int]) -> str` — used by `truncate.py` (Task 5) and `hooks/post_tool_use.py` (Task 7).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tokenizer.py`:

```python
from token_saver.tokenizer import count_tokens, encode, decode


def test_count_tokens_positive_for_nonempty_text():
    assert count_tokens("hello world") > 0


def test_count_tokens_empty_string_is_zero():
    assert count_tokens("") == 0


def test_count_tokens_matches_encode_length():
    text = "the quick brown fox jumps over the lazy dog"
    assert count_tokens(text) == len(encode(text))


def test_encode_decode_roundtrip():
    text = "def foo():\n    return 1 + 1\n"
    assert decode(encode(text)) == text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tokenizer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'token_saver.tokenizer'`.

- [ ] **Step 3: Implement `tokenizer.py`**

```python
import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_ENCODING.encode(text))


def encode(text: str) -> list[int]:
    return _ENCODING.encode(text)


def decode(tokens: list[int]) -> str:
    return _ENCODING.decode(tokens)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tokenizer.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/token_saver/tokenizer.py tests/test_tokenizer.py
git commit -m "feat: add tokenizer module (tiktoken-based approximation)"
```

---

### Task 2: `classifier.py`

**Files:**
- Create: `src/token_saver/classifier.py`
- Test: `tests/test_classifier.py`

**Interfaces:**
- Produces: `CommandType` enum (`TEST_RUNNER`, `GIT_DIFF`, `UNKNOWN`) and `classify_command(command: str) -> CommandType` — used by `hooks/post_tool_use.py` (Task 7).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_classifier.py`:

```python
import pytest

from token_saver.classifier import CommandType, classify_command


@pytest.mark.parametrize(
    "command,expected",
    [
        ("pytest tests/", CommandType.TEST_RUNNER),
        ("python -m pytest -v", CommandType.TEST_RUNNER),
        ("python3 -m pytest", CommandType.TEST_RUNNER),
        ("cd repo && pytest", CommandType.TEST_RUNNER),
        ("git diff HEAD~1", CommandType.GIT_DIFF),
        ("git diff --stat", CommandType.GIT_DIFF),
        ("git diff", CommandType.GIT_DIFF),
        ("ls -la", CommandType.UNKNOWN),
        ("npm test", CommandType.UNKNOWN),
        ("cat /home/user/pytest/README.md", CommandType.UNKNOWN),
        ("pytest_output.log", CommandType.UNKNOWN),
        ("echo 'running git diff now'", CommandType.UNKNOWN),
    ],
)
def test_classify_command(command, expected):
    assert classify_command(command) == expected
```

The `cat /home/user/pytest/README.md` and `pytest_output.log` cases exist because `pytest` appears as a substring that is *not* an invocation — the classifier must not false-positive on them. The `echo 'running git diff now'` case checks the same for `git diff` appearing inside a quoted string rather than as the actual command.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'token_saver.classifier'`.

- [ ] **Step 3: Implement `classifier.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_classifier.py -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add src/token_saver/classifier.py tests/test_classifier.py
git commit -m "feat: add command classifier (pytest / git diff / unknown)"
```

---

### Task 3: `extractors/__init__.py` + `extractors/pytest_extractor.py`

**Files:**
- Modify: `src/token_saver/extractors/__init__.py`
- Create: `src/token_saver/extractors/pytest_extractor.py`
- Create: `tests/fixtures/pytest_output/all_passed.txt`
- Create: `tests/fixtures/pytest_output/with_failures.txt`
- Create: `tests/fixtures/pytest_output/multiple_failures.txt`
- Create: `tests/fixtures/pytest_output/collection_error.txt`
- Test: `tests/test_pytest_extractor.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `ExtractionResult` dataclass (`text: str`, `metadata: dict`) in `token_saver.extractors`, and `extract_pytest(raw_output: str) -> ExtractionResult` in `token_saver.extractors.pytest_extractor` — both used by `hooks/post_tool_use.py` (Task 7). `extract_git_diff` (Task 4) also imports `ExtractionResult` from `token_saver.extractors`.

- [ ] **Step 1: Create the pytest output fixtures**

Create `tests/fixtures/pytest_output/all_passed.txt`:

```
============================= test session starts ==============================
platform linux -- Python 3.11.6, pytest-8.1.1, pluggy-1.4.0
rootdir: /home/user/project
collected 3 items

tests/test_math.py ...                                                     [100%]

============================== 3 passed in 0.05s ===============================
```

Create `tests/fixtures/pytest_output/with_failures.txt`:

```
============================= test session starts ==============================
platform linux -- Python 3.11.6, pytest-8.1.1, pluggy-1.4.0
rootdir: /home/user/project
collected 3 items

tests/test_math.py .F.                                                     [100%]

=================================== FAILURES ===================================
_________________________________ test_add_wrong _________________________________

    def test_add_wrong():
>       assert 1 + 1 == 3
E       assert 2 == 3

tests/test_math.py:5: AssertionError
=========================== short test summary info ============================
FAILED tests/test_math.py::test_add_wrong - assert 2 == 3
========================= 1 failed, 2 passed in 0.05s =========================
```

Create `tests/fixtures/pytest_output/multiple_failures.txt`:

```
============================= test session starts ==============================
platform linux -- Python 3.11.6, pytest-8.1.1, pluggy-1.4.0
rootdir: /home/user/project
collected 4 items

tests/test_math.py .FF.                                                     [100%]

=================================== FAILURES ===================================
_________________________________ test_add_wrong _________________________________

    def test_add_wrong():
>       assert 1 + 1 == 3
E       assert 2 == 3

tests/test_math.py:5: AssertionError
_________________________________ test_sub_wrong _________________________________

    def test_sub_wrong():
>       assert 5 - 2 == 10
E       assert 3 == 10

tests/test_math.py:9: AssertionError
=========================== short test summary info ============================
FAILED tests/test_math.py::test_add_wrong - assert 2 == 3
FAILED tests/test_math.py::test_sub_wrong - assert 3 == 10
======================= 2 failed, 2 passed in 0.06s ========================
```

Create `tests/fixtures/pytest_output/collection_error.txt`:

```
============================= test session starts ==============================
platform linux -- Python 3.11.6, pytest-8.1.1, pluggy-1.4.0
rootdir: /home/user/project
collected 0 items / 1 error

=================================== ERRORS ====================================
_________________________ ERROR collecting tests/test_broken.py _________________________
ImportError while importing test module 'tests/test_broken.py'.
tests/test_broken.py:1: in <module>
    import nonexistent_module
E   ModuleNotFoundError: No module named 'nonexistent_module'
=========================== short test summary info ============================
ERROR tests/test_broken.py
=============================== 1 error in 0.03s ===============================
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_pytest_extractor.py`:

```python
from pathlib import Path

from token_saver.extractors.pytest_extractor import extract_pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_extract_pytest_all_passed():
    raw = (FIXTURES_DIR / "pytest_output" / "all_passed.txt").read_text()
    result = extract_pytest(raw)
    assert result.metadata["counts"] == {"passed": 3}
    assert "FAILURES" not in result.text
    assert "passed" in result.text


def test_extract_pytest_with_failures():
    raw = (FIXTURES_DIR / "pytest_output" / "with_failures.txt").read_text()
    result = extract_pytest(raw)
    assert result.metadata["counts"] == {"failed": 1, "passed": 2}
    assert "test_add_wrong" in result.text
    assert "tests/test_math.py:5: AssertionError" in result.text
    assert "assert 2 == 3" in result.text
    assert "short test summary info" not in result.text
    assert "collected 3 items" not in result.text


def test_extract_pytest_multiple_failures():
    raw = (FIXTURES_DIR / "pytest_output" / "multiple_failures.txt").read_text()
    result = extract_pytest(raw)
    assert result.metadata["counts"] == {"failed": 2, "passed": 2}
    assert "test_add_wrong" in result.text
    assert "test_sub_wrong" in result.text
    assert "tests/test_math.py:5: AssertionError" in result.text
    assert "tests/test_math.py:9: AssertionError" in result.text


def test_extract_pytest_collection_error():
    raw = (FIXTURES_DIR / "pytest_output" / "collection_error.txt").read_text()
    result = extract_pytest(raw)
    assert result.metadata["counts"] == {"error": 1}
    assert "ModuleNotFoundError" in result.text
    assert "nonexistent_module" in result.text
    assert "short test summary info" not in result.text
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_pytest_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'token_saver.extractors.pytest_extractor'`.

- [ ] **Step 4: Implement `ExtractionResult` in `extractors/__init__.py`**

Replace the contents of `src/token_saver/extractors/__init__.py`:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 5: Implement `pytest_extractor.py`**

```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_pytest_extractor.py -v`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add src/token_saver/extractors/__init__.py src/token_saver/extractors/pytest_extractor.py tests/fixtures/pytest_output tests/test_pytest_extractor.py
git commit -m "feat: add pytest output extractor"
```

---

### Task 4: `extractors/git_diff_extractor.py`

**Files:**
- Create: `src/token_saver/extractors/git_diff_extractor.py`
- Create: `tests/fixtures/git_diff/single_hunk.diff`
- Create: `tests/fixtures/git_diff/multiple_hunks.diff`
- Create: `tests/fixtures/git_diff/multiple_files.diff`
- Create: `tests/fixtures/git_diff/binary_file.diff`
- Create: `tests/fixtures/git_diff/new_file.diff`
- Create: `tests/fixtures/git_diff/removed_file.diff`
- Test: `tests/test_git_diff_extractor.py`

**Interfaces:**
- Consumes: `ExtractionResult` from `token_saver.extractors` (Task 3).
- Produces: `extract_git_diff(raw_output: str, context_lines: int = 1) -> ExtractionResult` — used by `hooks/post_tool_use.py` (Task 7).

- [ ] **Step 1: Create the git diff fixtures**

Create `tests/fixtures/git_diff/single_hunk.diff` (note: context lines below start with exactly one leading space, the diff marker):

```
diff --git a/calc.py b/calc.py
index 1111111..2222222 100644
--- a/calc.py
+++ b/calc.py
@@ -1,10 +1,10 @@
 def add(a, b):
     return a + b
 
 
 def subtract(a, b):
-    return a - b
+    return a - b - 1
 
 
 def multiply(a, b):
     return a * b
```

Create `tests/fixtures/git_diff/multiple_hunks.diff`:

```
diff --git a/utils.py b/utils.py
index 3333333..4444444 100644
--- a/utils.py
+++ b/utils.py
@@ -2,3 +2,3 @@
 def helper_one():
-    return 1
+    return 2
@@ -10,3 +10,3 @@
 def helper_two():
-    return 10
+    return 20
```

Create `tests/fixtures/git_diff/multiple_files.diff`:

```
diff --git a/a.py b/a.py
index 1111111..2222222 100644
--- a/a.py
+++ b/a.py
@@ -1,2 +1,2 @@
 def a():
-    return 1
+    return 2
diff --git a/b.py b/b.py
index 3333333..4444444 100644
--- a/b.py
+++ b/b.py
@@ -1,2 +1,2 @@
 def b():
-    return 3
+    return 4
```

Create `tests/fixtures/git_diff/binary_file.diff`:

```
diff --git a/logo.png b/logo.png
index 5555555..6666666 100644
Binary files a/logo.png and b/logo.png differ
```

Create `tests/fixtures/git_diff/new_file.diff`:

```
diff --git a/new_module.py b/new_module.py
new file mode 100644
index 0000000..7777777
--- /dev/null
+++ b/new_module.py
@@ -0,0 +1,3 @@
+def new_function():
+    pass
+
```

Create `tests/fixtures/git_diff/removed_file.diff`:

```
diff --git a/old_module.py b/old_module.py
deleted file mode 100644
index 8888888..0000000
--- a/old_module.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def old_function():
-    pass
-
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_git_diff_extractor.py`:

```python
from pathlib import Path

from token_saver.extractors.git_diff_extractor import extract_git_diff

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "git_diff"


def test_extract_git_diff_single_hunk_collapses_long_context():
    raw = (FIXTURES_DIR / "single_hunk.diff").read_text()
    result = extract_git_diff(raw, context_lines=1)
    assert result.metadata["hunks"] == 1
    assert result.metadata["context_blocks_collapsed"] == 2
    assert "-    return a - b" in result.text
    assert "+    return a - b - 1" in result.text
    assert "linhas inalteradas omitidas" in result.text
    assert "return a + b" not in result.text
    assert "diff --git a/calc.py b/calc.py" in result.text


def test_extract_git_diff_multiple_hunks_same_file():
    raw = (FIXTURES_DIR / "multiple_hunks.diff").read_text()
    result = extract_git_diff(raw, context_lines=1)
    assert result.metadata["hunks"] == 2
    assert result.metadata["context_blocks_collapsed"] == 0
    assert "helper_one" in result.text
    assert "helper_two" in result.text


def test_extract_git_diff_multiple_files():
    raw = (FIXTURES_DIR / "multiple_files.diff").read_text()
    result = extract_git_diff(raw, context_lines=1)
    assert result.metadata["hunks"] == 2
    assert "diff --git a/a.py b/a.py" in result.text
    assert "diff --git a/b.py b/b.py" in result.text
    assert "def a():" in result.text
    assert "def b():" in result.text


def test_extract_git_diff_binary_file_preserved_without_parsing():
    raw = (FIXTURES_DIR / "binary_file.diff").read_text()
    result = extract_git_diff(raw, context_lines=1)
    assert result.metadata["hunks"] == 0
    assert "Binary files a/logo.png and b/logo.png differ" in result.text


def test_extract_git_diff_new_file():
    raw = (FIXTURES_DIR / "new_file.diff").read_text()
    result = extract_git_diff(raw, context_lines=1)
    assert result.metadata["hunks"] == 1
    assert result.metadata["context_blocks_collapsed"] == 0
    assert "+def new_function():" in result.text
    assert "new file mode 100644" in result.text


def test_extract_git_diff_removed_file():
    raw = (FIXTURES_DIR / "removed_file.diff").read_text()
    result = extract_git_diff(raw, context_lines=1)
    assert result.metadata["hunks"] == 1
    assert "-def old_function():" in result.text
    assert "deleted file mode 100644" in result.text
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_git_diff_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'token_saver.extractors.git_diff_extractor'`.

- [ ] **Step 4: Implement `git_diff_extractor.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_git_diff_extractor.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/token_saver/extractors/git_diff_extractor.py tests/fixtures/git_diff tests/test_git_diff_extractor.py
git commit -m "feat: add git diff extractor with context collapsing"
```

---

### Task 5: `truncate.py`

**Files:**
- Create: `src/token_saver/truncate.py`
- Test: `tests/test_truncate.py`

**Interfaces:**
- Consumes: `encode`, `decode` from `token_saver.tokenizer` (Task 1).
- Produces: `paired_truncate(raw_output: str, target_tokens: int) -> str` — used by `hooks/post_tool_use.py` (Task 7) to generate S2a.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_truncate.py`:

```python
from token_saver.tokenizer import count_tokens
from token_saver.truncate import paired_truncate


def test_paired_truncate_returns_original_if_within_budget():
    text = "short text"
    assert paired_truncate(text, target_tokens=100) == text


def test_paired_truncate_cuts_to_approximately_target_budget():
    text = "word " * 500
    result = paired_truncate(text, target_tokens=20)
    assert count_tokens(result) <= 25
    assert "truncado" in result


def test_paired_truncate_preserves_prefix_content():
    text = "FIRST_MARKER " + ("filler " * 300) + "LAST_MARKER"
    result = paired_truncate(text, target_tokens=5)
    assert "FIRST_MARKER" in result
    assert "LAST_MARKER" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_truncate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'token_saver.truncate'`.

- [ ] **Step 3: Implement `truncate.py`**

```python
from token_saver.tokenizer import decode, encode


def paired_truncate(raw_output: str, target_tokens: int) -> str:
    if target_tokens <= 0:
        return "... [saída omitida: orçamento de 0 tokens] ..."

    tokens = encode(raw_output)
    if len(tokens) <= target_tokens:
        return raw_output

    marker = f"\n... [truncado: {len(tokens) - target_tokens} tokens omitidos] ..."
    marker_tokens = len(encode(marker))
    keep = max(target_tokens - marker_tokens, 0)
    truncated_text = decode(tokens[:keep])
    return truncated_text + marker
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_truncate.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/token_saver/truncate.py tests/test_truncate.py
git commit -m "feat: add paired truncation baseline (S2a)"
```

---

### Task 6: `logger.py`

**Files:**
- Create: `src/token_saver/logger.py`
- Test: `tests/test_logger.py`

**Interfaces:**
- Produces: `EventRecord` dataclass (`timestamp`, `command`, `command_type`, `raw_output`, `raw_tokens`, `s2a_output`, `s2a_tokens`, `s2b_output`, `s2b_tokens`, `extractor_error: str | None = None`, `approx_fallback: bool = False`) and `log_event(event: EventRecord, path: Path) -> None` — used by `hooks/post_tool_use.py` (Task 7).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_logger.py`:

```python
import json

from token_saver.logger import EventRecord, log_event


def _sample_event(**overrides) -> EventRecord:
    defaults = dict(
        timestamp="2026-09-14T12:00:00Z",
        command="pytest",
        command_type="test_runner",
        raw_output="raw",
        raw_tokens=10,
        s2a_output="trunc",
        s2a_tokens=5,
        s2b_output="extracted",
        s2b_tokens=5,
    )
    defaults.update(overrides)
    return EventRecord(**defaults)


def test_log_event_appends_json_line(tmp_path):
    path = tmp_path / "events.jsonl"
    log_event(_sample_event(), path)
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["command"] == "pytest"
    assert record["command_type"] == "test_runner"
    assert record["extractor_error"] is None


def test_log_event_appends_multiple_events(tmp_path):
    path = tmp_path / "events.jsonl"
    for i in range(3):
        log_event(_sample_event(command="git diff", command_type="git_diff"), path)
    lines = path.read_text().splitlines()
    assert len(lines) == 3


def test_log_event_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "events.jsonl"
    log_event(_sample_event(extractor_error="boom"), path)
    record = json.loads(path.read_text().splitlines()[0])
    assert record["extractor_error"] == "boom"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_logger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'token_saver.logger'`.

- [ ] **Step 3: Implement `logger.py`**

```python
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class EventRecord:
    timestamp: str
    command: str
    command_type: str
    raw_output: str
    raw_tokens: int
    s2a_output: str
    s2a_tokens: int
    s2b_output: str
    s2b_tokens: int
    extractor_error: str | None = None
    approx_fallback: bool = False


def log_event(event: EventRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event), ensure_ascii=False))
        f.write("\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_logger.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/token_saver/logger.py tests/test_logger.py
git commit -m "feat: add JSONL event logger"
```

---

### Task 7: `hooks/post_tool_use.py`

**Files:**
- Create: `hooks/post_tool_use.py`
- Test: `tests/test_hook_post_tool_use.py`

**Interfaces:**
- Consumes: `CommandType`, `classify_command` (Task 2); `extract_pytest` (Task 3); `extract_git_diff` (Task 4); `count_tokens` (Task 1); `paired_truncate` (Task 5); `EventRecord`, `log_event` (Task 6).
- Produces: `process_event(payload: dict, data_path: Path) -> None` (testable core) and `main() -> int` (real stdin/stdout entrypoint) — `main` is what Task 8 wires into `.claude/settings.json`.

This task's hook payload shape (field names `tool_name`, `tool_input`, `tool_response`) and the observer exit contract (exit `0`, no required stdout) were verified against the official Claude Code hooks reference (`code.claude.com/docs/en/hooks.md`, `PostToolUse` section) before writing this task. For the `Bash` tool, `tool_input` carries a `command` field, and `tool_response` is `{"type": "text", "text": "<stdout/stderr content>"}`. The implementation below also tolerates a plain-string `tool_response` or one shaped like `{"stdout": ..., "stderr": ...}`, in case the exact shape varies by Claude Code version.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_hook_post_tool_use.py`:

```python
import json

from hooks.post_tool_use import process_event


def test_process_event_logs_pytest_event(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_response": {"type": "text", "text": "===== 2 passed in 0.01s ====="},
    }
    process_event(payload, data_path)
    lines = data_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["command_type"] == "test_runner"
    assert record["s2b_tokens"] > 0
    assert record["extractor_error"] is None


def test_process_event_ignores_non_bash_tool(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {"tool_name": "Read", "tool_input": {}, "tool_response": {}}
    process_event(payload, data_path)
    assert not data_path.exists()


def test_process_event_ignores_unknown_command(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "tool_response": {"type": "text", "text": "file1\nfile2"},
    }
    process_event(payload, data_path)
    assert not data_path.exists()


def test_process_event_logs_git_diff_event_with_string_tool_response(tmp_path):
    data_path = tmp_path / "events.jsonl"
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git diff"},
        "tool_response": "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-old\n+new\n",
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["command_type"] == "git_diff"
    assert "new" in record["s2b_output"]


def test_process_event_logs_extractor_error_without_raising(tmp_path, monkeypatch):
    data_path = tmp_path / "events.jsonl"

    def _raise(*args, **kwargs):
        raise ValueError("parse failed")

    monkeypatch.setattr("hooks.post_tool_use.extract_pytest", _raise)
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest"},
        "tool_response": {"type": "text", "text": "garbage"},
    }
    process_event(payload, data_path)
    record = json.loads(data_path.read_text().splitlines()[0])
    assert record["extractor_error"] == "parse failed"
    assert record["s2b_output"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_hook_post_tool_use.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hooks.post_tool_use'`.

- [ ] **Step 3: Implement `hooks/post_tool_use.py`**

```python
#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from token_saver.classifier import CommandType, classify_command
from token_saver.extractors.git_diff_extractor import extract_git_diff
from token_saver.extractors.pytest_extractor import extract_pytest
from token_saver.logger import EventRecord, log_event
from token_saver.tokenizer import count_tokens
from token_saver.truncate import paired_truncate

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "events.jsonl"


def _extract_output_text(tool_response) -> str:
    if isinstance(tool_response, str):
        return tool_response
    if isinstance(tool_response, dict):
        if "text" in tool_response:
            return tool_response["text"]
        parts = [tool_response.get("stdout", ""), tool_response.get("stderr", "")]
        return "\n".join(p for p in parts if p)
    return ""


def process_event(payload: dict, data_path: Path) -> None:
    if payload.get("tool_name") != "Bash":
        return

    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "")
    if not command:
        return

    command_type = classify_command(command)
    if command_type is CommandType.UNKNOWN:
        return

    raw_output = _extract_output_text(payload.get("tool_response"))

    extractor_error = None
    s2b_output = ""
    try:
        if command_type is CommandType.TEST_RUNNER:
            s2b_output = extract_pytest(raw_output).text
        elif command_type is CommandType.GIT_DIFF:
            s2b_output = extract_git_diff(raw_output).text
    except Exception as exc:  # extractor must never crash the real session
        extractor_error = str(exc)

    try:
        raw_tokens = count_tokens(raw_output)
        s2b_tokens = count_tokens(s2b_output)
        approx_fallback = False
    except Exception:
        raw_tokens = len(raw_output) // 4
        s2b_tokens = len(s2b_output) // 4
        approx_fallback = True

    s2a_output = paired_truncate(raw_output, target_tokens=s2b_tokens) if s2b_output else ""
    s2a_tokens = count_tokens(s2a_output) if s2a_output else 0

    event = EventRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        command=command,
        command_type=command_type.value,
        raw_output=raw_output,
        raw_tokens=raw_tokens,
        s2a_output=s2a_output,
        s2a_tokens=s2a_tokens,
        s2b_output=s2b_output,
        s2b_tokens=s2b_tokens,
        extractor_error=extractor_error,
        approx_fallback=approx_fallback,
    )
    log_event(event, data_path)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    process_event(payload, DATA_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_hook_post_tool_use.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests across every module pass (tokenizer, classifier, pytest extractor, git diff extractor, truncate, logger, hook).

- [ ] **Step 6: Commit**

```bash
git add hooks/post_tool_use.py tests/test_hook_post_tool_use.py
git commit -m "feat: add PostToolUse hook entrypoint (log-only mode)"
```

---

### Task 8: Register the hook and verify it live

**Files:**
- Create: `.claude/settings.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: `hooks/post_tool_use.py`'s `main()` (Task 7) as an external process invoked by Claude Code.
- Produces: nothing consumed by later tasks — this is the final integration/verification step for this plan.

- [ ] **Step 1: Create `.claude/settings.json`**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python hooks/post_tool_use.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

This is a **project-level** hook (scoped to `Token-Saver/`), deliberately not installed at the user level yet — live data collection across other repositories is a decision for the Fase 3 spec, not this plan.

- [ ] **Step 2: Restart Claude Code / reload hooks**

Run inside the `Token-Saver` directory: `claude` (or, if already running there, run `/hooks` to confirm `PostToolUse` → `Bash` → `uv run python hooks/post_tool_use.py` is listed as registered).

- [ ] **Step 3: Manually trigger a `git diff` event and verify it was logged**

In a live Claude Code session inside `Token-Saver/`, make a trivial change (e.g. append a comment to `README.md`) and ask Claude Code to run `git diff`. After it runs, check:

Run: `tail -n 1 data/events.jsonl | python3 -m json.tool`
Expected: a JSON object with `"command_type": "git_diff"` and non-empty `s2b_output`.

Revert the trivial change afterward (`git checkout -- README.md` or equivalent) so it doesn't pollute Task 8's own commit.

- [ ] **Step 4: Manually trigger a `pytest` event and verify it was logged**

In the same live session, ask Claude Code to run `uv run pytest`. After it runs, check:

Run: `tail -n 1 data/events.jsonl | python3 -m json.tool`
Expected: a JSON object with `"command_type": "test_runner"` and `s2b_output` containing `"Resumo:"`.

- [ ] **Step 5: Confirm the real session was unaffected**

Verify Claude Code's own transcript shows the *raw* `git diff` / `pytest` output (not the compressed version) — this confirms the hook is running in pure log/observer mode as specified, never altering what the agent actually sees.

- [ ] **Step 6: Finalize `README.md`**

Replace the contents of `README.md`:

```markdown
# Token Saver

Protótipo de extratores determinísticos para saídas de ferramentas do Claude Code — TCC, Fases 0–2 do escopo de 80h (classificador, extratores de `pytest`/`git diff`, truncamento pareado, logger).

Spec: `docs/superpowers/specs/2026-09-14-extractors-prototype-design.md`
Plano de implementação: `docs/superpowers/plans/2026-09-14-extractors-prototype.md`

## Setup

\`\`\`bash
uv sync
\`\`\`

## Rodar os testes

\`\`\`bash
uv run pytest
\`\`\`

## Hook

O hook `PostToolUse` (`hooks/post_tool_use.py`) roda em **modo log**: observa chamadas da tool `Bash` que casem com `pytest` ou `git diff`, grava um evento por chamada em `data/events.jsonl` (comando, saída bruta, versão truncada pareada S2a, versão extraída S2b, contagem de tokens de cada uma), e nunca altera o que o agente vê. Registrado em `.claude/settings.json` (escopo de projeto).

`data/*.jsonl` é gitignored — pode conter código dos repositórios usados durante a coleta.

## Fora de escopo (por enquanto)

Coleta de dataset ao vivo em múltiplos repositórios, réplica contrafactual via API, análise estatística (teste de McNemar) — ver a spec para o raciocínio completo.
```

- [ ] **Step 7: Commit**

```bash
git add .claude/settings.json README.md
git commit -m "chore: register PostToolUse hook and finalize README"
```

---

## Self-review notes

- **Spec coverage:** every component in spec §3 (classifier, pytest extractor, git diff extractor, tokenizer, truncate, logger, hook) has a task; spec §5 (error handling) is implemented in Task 7 and matches the spec's exact resolution (event still logged, `s2b_output` empty, `extractor_error` set); spec §6 (testing) fixtures match 1:1 (pytest: all-pass/one-failure/multi-failure/collection-error; git diff: single hunk/multiple hunks/multiple files/binary/new file/removed file); spec §7 (project structure) matches Task 0's scaffolding; spec §8 (completion criteria) is verified live in Task 8.
- **Placeholder scan:** no TBD/TODO; every code step has runnable code; every test has real assertions against real fixtures.
- **Type consistency:** `CommandType.value` (Task 2) feeds `EventRecord.command_type: str` (Task 6) via `command_type.value` in Task 7 — consistent. `ExtractionResult.text` (Task 3) is what both extractors return and what Task 7 reads via `.text` — consistent across Tasks 3, 4, 7. `encode`/`decode` (Task 1) are the exact names `truncate.py` imports (Task 5) — consistent.
