import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class EventRecord:
    timestamp: str
    command: str
    command_type: str
    raw_output: str
    raw_tokens: int
    s2a_output: str
    s2a_tokens: int
    s2b_output: str
    s2b_tokens: int
    extractor_error: str | None = None
    approx_fallback: bool = False


def log_event(event: EventRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event), ensure_ascii=False))
        f.write("\n")
