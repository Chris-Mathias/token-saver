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
    result = paired_truncate(text, target_tokens=20)
    assert "FIRST_MARKER" in result
    assert "LAST_MARKER" not in result
