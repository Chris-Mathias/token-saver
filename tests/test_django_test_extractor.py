from pathlib import Path

from token_saver.extractors.django_test_extractor import extract_django_test

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "django_test_output"


def test_extract_django_all_passed():
    raw = (FIXTURES_DIR / "all_passed.txt").read_text()
    result = extract_django_test(raw)
    assert result.metadata["parsed"] is True
    assert result.metadata["counts"] == {"total": 2}
    assert result.metadata["ok"] is True
    assert result.text == "Resumo: 2 testes — OK"


def test_extract_django_with_failures_keeps_traceback():
    raw = (FIXTURES_DIR / "with_failures.txt").read_text()
    result = extract_django_test(raw)
    assert result.metadata["ok"] is False
    assert result.metadata["counts"] == {"total": 3, "failures": 1}
    assert "FAIL: test_aplica_desconto" in result.text
    assert "AssertionError: 10 != 9" in result.text
    assert 'File "/home/user/project/shop/tests.py", line 13' in result.text


def test_extract_django_drops_noise_lines():
    raw = (FIXTURES_DIR / "with_failures.txt").read_text()
    result = extract_django_test(raw)
    assert "Creating test database" not in result.text
    assert "Destroying test database" not in result.text
    assert "System check identified no issues" not in result.text
    assert "Found 3 test(s)" not in result.text
    assert "=====" not in result.text


def test_extract_django_failures_and_errors_together():
    raw = (FIXTURES_DIR / "failures_and_errors.txt").read_text()
    result = extract_django_test(raw)
    assert result.metadata["counts"] == {"total": 5, "failures": 1, "errors": 1}
    assert "ERROR: test_divide" in result.text
    assert "ZeroDivisionError: division by zero" in result.text
    assert "FAIL: test_aplica_desconto" in result.text


def test_extract_django_verbose_drops_migration_noise():
    raw = (FIXTURES_DIR / "verbose_with_failures.txt").read_text()
    result = extract_django_test(raw)
    assert result.metadata["parsed"] is True
    assert "Applying auth.0001_initial" not in result.text
    assert "Synchronizing apps without migrations" not in result.text
    assert "ERROR: test_divide" in result.text


def test_extract_django_unrecognized_output_is_returned_as_is():
    raw = "===== 2 passed in 0.01s =====\n"
    result = extract_django_test(raw)
    assert result.metadata == {"parsed": False}
    assert result.text == raw.strip()
