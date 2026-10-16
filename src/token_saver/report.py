"""Resumo de um arquivo de eventos: economia de tokens e um proxy de fidelidade.

Uso: uv run python -m token_saver.report data/events.jsonl
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Django/unittest: "FAIL: test_x (mod.Class.test_x)"; vitest: " FAIL  arquivo"
# para suítes que nem carregaram e "× nome do teste 12ms" para testes falhos.
_MARKER_RES = [
    re.compile(r"^(?:FAIL|ERROR): (\S+)", re.MULTILINE),
    re.compile(r"^\s*FAIL\s{2,}(\S+)", re.MULTILINE),
    re.compile(r"^\s*[×✗] (.+?)(?: \d+ms)?$", re.MULTILINE),
]


def failure_markers(raw_output: str) -> list[str]:
    found: list[tuple[int, str]] = []
    for pattern in _MARKER_RES:
        found.extend((m.start(), m.group(1)) for m in pattern.finditer(raw_output))
    markers: list[str] = []
    for _, marker in sorted(found):
        if marker not in markers:
            markers.append(marker)
    return markers


def _parsed(event: dict) -> bool:
    return bool((event.get("s2b_metadata") or {}).get("parsed", True))


def _failed(event: dict) -> bool:
    return (event.get("exit_code") or 0) != 0


@dataclass
class Slice:
    label: str
    events: int
    raw_tokens: int
    s2b_tokens: int

    @property
    def reduction(self) -> float:
        return 1 - self.s2b_tokens / self.raw_tokens if self.raw_tokens else 0.0


def _slice(label: str, events: list[dict]) -> Slice:
    return Slice(
        label=label,
        events=len(events),
        raw_tokens=sum(e["raw_tokens"] for e in events),
        s2b_tokens=sum(e["s2b_tokens"] for e in events),
    )


def summarize(events: list[dict]) -> list[Slice]:
    parsed = [e for e in events if _parsed(e)]
    slices = [
        _slice("Total", events),
        _slice("Interpretadas", parsed),
        _slice("Não interpretadas", [e for e in events if not _parsed(e)]),
        _slice("Interpretadas, sucesso", [e for e in parsed if not _failed(e)]),
        _slice("Interpretadas, falha", [e for e in parsed if _failed(e)]),
    ]
    types = sorted({e["command_type"] for e in events})
    slices += [_slice(t, [e for e in events if e["command_type"] == t]) for t in types]
    return slices


@dataclass
class Fidelity:
    events: int = 0
    markers: int = 0
    kept_s2a: int = 0
    kept_s2b: int = 0
    events_s2a_lost: int = 0
    events_s2b_lost: int = 0


def fidelity(events: list[dict]) -> Fidelity:
    """Quantos identificadores de falha do bruto sobrevivem em S2a e em S2b.

    Proxy barato da fidelidade de decisão: se o agente não vê qual teste
    falhou, dificilmente toma a mesma próxima ação. Só considera eventos com
    falha que o extrator interpretou, onde S2a e S2b têm o mesmo orçamento.
    """
    result = Fidelity()
    for event in events:
        if not (_failed(event) and _parsed(event)):
            continue
        markers = failure_markers(event["raw_output"])
        if not markers:
            continue
        in_s2a = sum(m in event["s2a_output"] for m in markers)
        in_s2b = sum(m in event["s2b_output"] for m in markers)
        result.events += 1
        result.markers += len(markers)
        result.kept_s2a += in_s2a
        result.kept_s2b += in_s2b
        result.events_s2a_lost += in_s2a < len(markers)
        result.events_s2b_lost += in_s2b < len(markers)
    return result


def _pct(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "—"


def render(events: list[dict]) -> str:
    lines = [
        "| Recorte | Eventos | Tokens brutos | Tokens S2b | Redução |",
        "|---|---:|---:|---:|---:|",
    ]
    for s in summarize(events):
        lines.append(
            f"| {s.label} | {s.events} | {s.raw_tokens} | {s.s2b_tokens} | {s.reduction:.0%} |"
        )
    f = fidelity(events)
    lines += [
        "",
        f"Proxy de fidelidade ({f.events} eventos com falha interpretados, "
        f"{f.markers} identificadores de falha no bruto):",
        "",
        "| Versão | Identificadores preservados | Eventos com perda |",
        "|---|---:|---:|",
        f"| S2a (truncamento) | {f.kept_s2a}/{f.markers} ({_pct(f.kept_s2a, f.markers)}) "
        f"| {f.events_s2a_lost}/{f.events} |",
        f"| S2b (extrator) | {f.kept_s2b}/{f.markers} ({_pct(f.kept_s2b, f.markers)}) "
        f"| {f.events_s2b_lost}/{f.events} |",
    ]
    return "\n".join(lines)


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


if __name__ == "__main__":
    print(render(load(Path(sys.argv[1] if len(sys.argv) > 1 else "data/events.jsonl"))))
