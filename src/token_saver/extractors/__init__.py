from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
