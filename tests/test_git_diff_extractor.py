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
    assert "+++ b/a.py" in result.text
    assert "+++ b/b.py" in result.text
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


def test_extract_git_diff_drops_redundant_file_header_lines():
    raw = (FIXTURES_DIR / "single_hunk.diff").read_text()
    result = extract_git_diff(raw)
    assert "diff --git" not in result.text
    assert "index 1111111..2222222" not in result.text
    assert "--- a/calc.py" in result.text
    assert "+++ b/calc.py" in result.text
    assert result.metadata["header_lines_removed"] == 2


def test_extract_git_diff_default_omits_all_context_runs():
    raw = (FIXTURES_DIR / "single_hunk.diff").read_text()
    result = extract_git_diff(raw)
    assert result.metadata["context_blocks_collapsed"] == 2
    assert "... 5 linhas inalteradas omitidas ..." in result.text
    assert "... 4 linhas inalteradas omitidas ..." in result.text
    assert "def subtract" not in result.text
    assert "@@ -1,10 +1,10 @@" in result.text
    assert "+    return a - b - 1" in result.text


def test_extract_git_diff_keeps_single_line_context_run():
    raw = (
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,3 +1,3 @@\n"
        "-a = 1\n"
        "+a = 2\n"
        " b = 2\n"
        "-c = 3\n"
        "+c = 4\n"
    )
    result = extract_git_diff(raw)
    assert " b = 2" in result.text
    assert "omitidas" not in result.text


def test_extract_git_diff_keeps_git_header_when_it_is_the_only_file_name():
    raw = (
        "diff --git a/run.sh b/run.sh\n"
        "old mode 100644\n"
        "new mode 100755\n"
    )
    result = extract_git_diff(raw)
    assert "diff --git a/run.sh b/run.sh" in result.text
    assert "new mode 100755" in result.text
