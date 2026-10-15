import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


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
    s2b_metadata: dict[str, Any] = field(default_factory=dict)
    extractor_error: str | None = None
    approx_fallback: bool = False
    exit_code: int | None = None
    # Identify where this call sits in the real session, so the decision the
    # agent took after seeing the raw output can be recovered from the
    # transcript when the counterfactual replay is built.
    session_id: str | None = None
    transcript_path: str | None = None
    cwd: str | None = None
    tool_use_id: str | None = None
    command_segments: int = 1
    has_heredoc: bool = False
    truncating_pipe: bool = False


def log_event(event: EventRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
