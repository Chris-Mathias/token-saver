from token_saver.tokenizer import decode, encode


def paired_truncate(raw_output: str, target_tokens: int) -> str:
    if target_tokens <= 0:
        return "... [saída omitida: orçamento de 0 tokens] ..."

    tokens = encode(raw_output)
    if len(tokens) <= target_tokens:
        return raw_output

    marker = f"\n... [truncado: {len(tokens) - target_tokens} tokens omitidos] ..."
    marker_tokens = len(encode(marker))
    keep = max(target_tokens - marker_tokens, 0)
    truncated_text = decode(tokens[:keep])
    return truncated_text + marker
