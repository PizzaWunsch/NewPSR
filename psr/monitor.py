from __future__ import annotations
from typing import List, Optional, Tuple
import mss

from .models import MonitorInfo


def list_monitors() -> List[MonitorInfo]:
    sct = mss.mss()
    mons = []
    for i in range(1, len(sct.monitors)):
        m = sct.monitors[i]
        mons.append(MonitorInfo(index=i, left=m["left"], top=m["top"], width=m["width"], height=m["height"]))
    return mons


def find_monitor_for_point(monitors: List[MonitorInfo], x: int, y: int) -> Optional[Tuple[MonitorInfo, int, int]]:

    for m in monitors:
        if m.left <= x < m.left + m.width and m.top <= y < m.top + m.height:
            return m, x - m.left, y - m.top
    return None