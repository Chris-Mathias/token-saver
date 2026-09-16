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


def test_extract_pytest_handles_long_duration_suffix():
    raw = (FIXTURES_DIR / "pytest_output" / "long_duration.txt").read_text()
    result = extract_pytest(raw)
    assert result.metadata["parsed"] is True
    assert result.metadata["counts"] == {"failed": 1, "passed": 2}
    assert "test_slow_fail" in result.text


def test_extract_pytest_failures_and_errors_together():
    raw = (FIXTURES_DIR / "pytest_output" / "failures_and_errors.txt").read_text()
    result = extract_pytest(raw)
    assert result.metadata["counts"] == {"failed": 1, "passed": 1, "error": 1}
    assert "ModuleNotFoundError" in result.text
    assert "nonexistent_module" in result.text
    assert "test_add_wrong" in result.text
    assert "tests/test_math.py:5: AssertionError" in result.text
