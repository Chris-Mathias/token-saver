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
