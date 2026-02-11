from __future__ import annotations

import re
from typing import Any, Dict, Optional


def _extract_xy(detail: str) -> Optional[tuple[int, int]]:
    m = re.search(r"\((\-?\d+),(\-?\d+)\)", detail)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _human_button(detail: str) -> str:
    d = (detail or "").lower()
    if "button.right" in d:
        return "Rechtsklick"
    if "button.middle" in d:
        return "Mittelklick"
    return "Klick"


def _human_key(detail: str) -> str:
    d = (detail or "").strip()
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


def _ctx(e: Dict[str, Any]) -> str:
    app = (e.get("app_name") or "").strip()
    title = (e.get("window_title") or "").strip()
    if app and title:
        return f"{app} ({title})"
    if app:
        return f"{app}"
    if title:
        return f"{title}"
    return ""


def generate_instruction(event: Dict[str, Any]) -> str:
    kind = (event.get("kind") or "").lower()
    detail = event.get("detail") or ""
    ctx = _ctx(event)
    prefix = (ctx + ": ") if ctx else ""

    if kind == "text_input":
        txt = (event.get("input_text") or "").strip()
        if txt:
            return f"{prefix}Text eingeben: {txt}"
        return f"{prefix}Text eingeben."

    if kind == "mouse_click":
        b = _human_button(detail)
        xy = _extract_xy(detail)
        if xy:
            return f"{prefix}{b} auf den markierten Bereich."
        return f"{prefix}{b} ausführen."

    if kind == "key_press":
        k = _human_key(detail)
        return f"{prefix}Taste drücken: {k}."

    return (prefix + (detail.strip() or "Schritt ausführen.")).strip()


def enrich_steps_json(data: Dict[str, Any]) -> Dict[str, Any]:
    events = data.get("events") or []
    for e in events:
        if isinstance(e, dict) and e.get("kind") in ("mouse_click", "key_press", "text_input"):
            e["instruction"] = generate_instruction(e)
    data["events"] = events
    return data