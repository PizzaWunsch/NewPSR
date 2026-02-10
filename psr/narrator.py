# psr/narrator.py
from __future__ import annotations

import re
from typing import Any, Dict, Optional


def _human_button(detail: str) -> str:
    d = detail.lower()
    if "button.left" in d:
        return "Linksklick"
    if "button.right" in d:
        return "Rechtsklick"
    if "button.middle" in d:
        return "Mittelklick"
    return "Klick"


def _extract_xy(detail: str) -> Optional[tuple[int, int]]:
    m = re.search(r"\((\-?\d+),(\-?\d+)\)", detail)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _human_key(detail: str) -> str:
    d = detail.strip()
    m = re.search(r"key:\s*(.+)$", d, re.IGNORECASE)
    if not m:
        return d
    k = m.group(1).strip().lower()
    mapping = {
        "enter": "Enter",
        "tab": "Tab",
        "esc": "Esc",
        "space": "Leertaste",
        "backspace": "Backspace",
        "ctrl_l": "Strg",
        "ctrl_r": "Strg",
        "alt_l": "Alt",
        "alt_r": "Alt",
        "shift": "Shift",
        "shift_l": "Shift",
        "shift_r": "Shift",
        "cmd": "Cmd",
        "cmd_l": "Cmd",
        "cmd_r": "Cmd",
    }
    return mapping.get(k, k)


def generate_instruction(event: Dict[str, Any]) -> str:
    kind = (event.get("kind") or "").lower()
    detail = event.get("detail") or ""

    if kind == "text_input":
        txt = event.get("input_text") or ""
        if txt:
            return f"Gib folgenden Text ein: {txt}"
        return "Gib Text ein."

    if kind == "mouse_click":
        b = _human_button(detail)
        xy = _extract_xy(detail)
        mon = event.get("monitor_index")
        if xy and mon:
            return f"Klicke auf Monitor {mon} an Position ({xy[0]},{xy[1]})."
        if xy:
            return f"Klicke an Position ({xy[0]},{xy[1]})."
        return f"Führe einen {b} aus."

    if kind == "key_press":
        k = _human_key(detail)
        return f"Drücke {k}."

    return detail.strip() or "Führe den Schritt aus."


def enrich_steps_json(data: Dict[str, Any]) -> Dict[str, Any]:
    events = data.get("events") or []
    for e in events:
        if isinstance(e, dict) and e.get("kind") in ("mouse_click", "key_press", "text_input"):
            e["instruction"] = generate_instruction(e)
    data["events"] = events
    return data
