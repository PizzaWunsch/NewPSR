# psr/models.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class MonitorInfo:
    index: int
    left: int
    top: int
    width: int
    height: int

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StepEvent:
    t: float
    kind: str
    detail: str
    monitor_index: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    rel_x: Optional[int] = None
    rel_y: Optional[int] = None
    screenshot: Optional[str] = None
    input_text: Optional[str] = None
    instruction: Optional[str] = None
