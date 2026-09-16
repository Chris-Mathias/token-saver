from token_saver.tokenizer import decode, encode


def paired_truncate(raw_output: str, target_tokens: int) -> str:
    if target_tokens <= 0:
        return ""

    tokens = encode(raw_output)
    if len(tokens) <= target_tokens:
        return raw_output

    marker = f"\n... [truncado: {len(tokens) - target_tokens} tokens omitidos] ..."
    marker_tokens_list = encode(marker)

    if len(marker_tokens_list) >= target_tokens:
        # Budget too small even for the marker alone: truncate the marker itself
        # so the result never exceeds target_tokens — this invariant is what
        # makes the S2a/S2b comparison fair at every budget size, including
        # very small ones (e.g. an all-passing pytest run's ~6-token S2b).
        return decode(marker_tokens_list[:target_tokens])

    keep = target_tokens - len(marker_tokens_list)
    truncated_text = decode(tokens[:keep])
    return truncated_text + marker
