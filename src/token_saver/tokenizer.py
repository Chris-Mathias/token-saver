import tiktoken

_encoding = None


def _get_encoding():
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_get_encoding().encode(text))


def encode(text: str) -> list[int]:
    return _get_encoding().encode(text)


def decode(tokens: list[int]) -> str:
    return _get_encoding().decode(tokens)
