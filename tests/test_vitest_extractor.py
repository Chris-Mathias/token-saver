from pathlib import Path

from token_saver.extractors.vitest_extractor import extract_vitest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "vitest_output"


def test_extract_vitest_all_passed():
    raw = (FIXTURES_DIR / "all_passed.txt").read_text()
    result = extract_vitest(raw)
    assert result.metadata["parsed"] is True
    assert result.metadata["counts"] == {"passed": 2, "total": 2}
    assert result.text == "Resumo: 2 passed (2) (arquivos: 1 passed (1))"


def test_extract_vitest_with_failures_keeps_failure_blocks():
    raw = (FIXTURES_DIR / "with_failures.txt").read_text()
    result = extract_vitest(raw)
    assert result.metadata["counts"] == {"failed": 2, "passed": 1, "total": 3}
    assert "FAIL  src/cart.test.js > cart > aplica desconto" in result.text
    assert "AssertionError: expected 10 to be 9" in result.text
    assert "src/cart.test.js:5:66" in result.text


def test_extract_vitest_drops_noise_lines():
    raw = (FIXTURES_DIR / "with_failures.txt").read_text()
    result = extract_vitest(raw)
    assert "RUN  v4" not in result.text
    assert "Start at" not in result.text
    assert "Duration" not in result.text
    assert "× aplica desconto" not in result.text
    assert "⎯" not in result.text


def test_extract_vitest_keeps_failed_suites_section():
    raw = (FIXTURES_DIR / "failures_and_import_error.txt").read_text()
    result = extract_vitest(raw)
    assert result.metadata["counts"] == {"failed": 2, "passed": 3, "total": 5}
    assert result.metadata["file_counts"] == {"failed": 2, "passed": 1, "total": 3}
    assert "FAIL  src/broken.test.js" in result.text
    assert "Cannot find module './does-not-exist.js'" in result.text
    assert "FAIL  src/cart.test.js > cart > retorna objeto" in result.text


def test_extract_vitest_through_npm_test_drops_npm_banner():
    raw = (FIXTURES_DIR / "npm_test_all_passed.txt").read_text()
    result = extract_vitest(raw)
    assert result.metadata["parsed"] is True
    assert "vitestdemo@1.0.0" not in result.text


def test_extract_vitest_unrecognized_output_is_returned_as_is():
    raw = "PASS ok/math.test.js\n\nTests:       3 passed, 3 total\n"
    result = extract_vitest(raw)
    assert result.metadata == {"parsed": False}
    assert result.text == raw.strip()
