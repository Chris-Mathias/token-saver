from pathlib import Path

from token_saver.extractors.jest_extractor import extract_jest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "jest_output"


def test_extract_jest_all_passed():
    raw = (FIXTURES_DIR / "all_passed.txt").read_text()
    result = extract_jest(raw)
    assert result.metadata["parsed"] is True
    assert result.metadata["counts"] == {"passed": 3, "total": 3}
    assert result.text == "Resumo: 3 passed, 3 total (suítes: 2 passed, 2 total)"


def test_extract_jest_with_failures_keeps_failure_blocks():
    raw = (FIXTURES_DIR / "with_failures.txt").read_text()
    result = extract_jest(raw)
    assert result.metadata["counts"] == {"failed": 2, "passed": 1, "total": 3}
    assert "FAIL fail/cart.test.js" in result.text
    assert "● cart › applies discount" in result.text
    assert "● cart › returns object" in result.text
    assert "Expected: 9" in result.text
    assert "at Object.toBe (fail/cart.test.js:5:36)" in result.text


def test_extract_jest_drops_noise_lines():
    raw = (FIXTURES_DIR / "with_failures.txt").read_text()
    result = extract_jest(raw)
    assert "✓ sums prices" not in result.text
    assert "✕ applies discount" not in result.text
    assert "Snapshots:" not in result.text
    assert "Time:" not in result.text
    assert "Ran all test suites" not in result.text


def test_extract_jest_suite_that_failed_to_run():
    raw = (FIXTURES_DIR / "failures_and_suite_error.txt").read_text()
    result = extract_jest(raw)
    assert result.metadata["suite_counts"] == {"failed": 2, "passed": 2, "total": 4}
    assert "FAIL fail/broken.test.js" in result.text
    assert "● Test suite failed to run" in result.text
    assert "Cannot find module './does-not-exist'" in result.text
    assert "PASS ok/math.test.js" not in result.text


def test_extract_jest_drops_node_modules_stack_frames():
    raw = (FIXTURES_DIR / "failures_and_suite_error.txt").read_text()
    result = extract_jest(raw)
    assert "node_modules/jest-resolve" not in result.text
    assert "at Object.<anonymous> (fail/broken.test.js:1:44)" in result.text


def test_extract_jest_silent_mode():
    raw = (FIXTURES_DIR / "silent_with_failures.txt").read_text()
    result = extract_jest(raw)
    assert result.metadata["counts"] == {"failed": 2, "passed": 1, "total": 3}
    assert "● cart › returns object" in result.text


def test_extract_jest_through_npm_test_drops_npm_banner():
    raw = (FIXTURES_DIR / "npm_test_all_passed.txt").read_text()
    result = extract_jest(raw)
    assert result.metadata["parsed"] is True
    assert "jestdemo@1.0.0" not in result.text


def test_extract_jest_unrecognized_output_is_returned_as_is():
    raw = " RUN  v1.6.0 /app\n ✓ src/a.test.ts (2)\n Test Files  1 passed (1)\n"
    result = extract_jest(raw)
    assert result.metadata == {"parsed": False}
    assert result.text == raw.strip()


def test_extract_jest_ignores_repeated_failure_summary():
    raw = (FIXTURES_DIR / "many_suites_repeats_failures.txt").read_text()
    result = extract_jest(raw)
    assert result.metadata["counts"] == {"failed": 2, "passed": 22, "total": 24}
    assert result.text.count("● cart › applies discount") == 1
    assert "Summary of all failing tests" not in result.text
