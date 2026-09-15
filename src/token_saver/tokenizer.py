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
