from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedDocument:
    parent_id: str
    source: str
    source_type: str
    title: str
    content: str
    author: str = ""
    url: str = ""
    updated_at: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
