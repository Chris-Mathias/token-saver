"""Gera um HTML autocontido para explorar um arquivo de eventos.

Uso: uv run python -m token_saver.viewer data/site-iecb.jsonl [saida.html]

O HTML embute as saídas brutas, então fica local (data/*.html é gitignored):
nada é carregado de fora nem enviado a lugar nenhum.
"""

import json
import re
import sys
from pathlib import Path

from token_saver.report import failure_markers, fidelity, load, summarize

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_TEMPLATE = Path(__file__).with_name("viewer_template.html")


def _clean(text: str) -> str:
    return _ANSI_RE.sub("", text or "")


def event_view(event: dict) -> dict:
    raw, s2a, s2b = (_clean(event.get(k, "")) for k in ("raw_output", "s2a_output", "s2b_output"))
    failed = (event.get("exit_code") or 0) != 0
    return {
        "timestamp": event.get("timestamp", ""),
        "command": event.get("command", ""),
        "command_type": event.get("command_type", ""),
        "exit_code": event.get("exit_code"),
        "failed": failed,
        "parsed": bool((event.get("s2b_metadata") or {}).get("parsed", True)),
        "metadata": event.get("s2b_metadata") or {},
        "extractor_error": event.get("extractor_error"),
        "command_segments": event.get("command_segments", 1),
        "truncating_pipe": event.get("truncating_pipe", False),
        "raw_tokens": event.get("raw_tokens", 0),
        "s2a_tokens": event.get("s2a_tokens", 0),
        "s2b_tokens": event.get("s2b_tokens", 0),
        "raw_output": raw,
        "s2a_output": s2a,
        "s2b_output": s2b,
        "markers": [
            {"name": m, "s2a": m in s2a, "s2b": m in s2b}
            for m in (failure_markers(raw) if failed else [])
        ],
    }


def _json_for_script(value) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def build_html(events: list[dict], source: str = "") -> str:
    slices = [
        {"label": s.label, "events": s.events, "raw": s.raw_tokens, "s2b": s.s2b_tokens}
        for s in summarize(events)
    ]
    f = fidelity(events)
    summary = {"source": source, "slices": slices, "fidelity": vars(f)}
    return (
        _TEMPLATE.read_text(encoding="utf-8")
        .replace("__SUMMARY__", _json_for_script(summary))
        .replace("__EVENTS__", _json_for_script([event_view(e) for e in events]))
    )


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/events.jsonl")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")
    out.write_text(build_html(load(src), source=src.name), encoding="utf-8")
    print(out.resolve())
