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
