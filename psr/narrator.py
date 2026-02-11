# narrator.py
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


def _extract_xy(detail: str) -> Optional[tuple[int, int]]:
    m = re.search(r"\((\-?\d+),(\-?\d+)\)", detail or "")
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
        "escape": "Esc",
        "space": "Leertaste",
        "backspace": "Backspace",
        "ctrl_l": "Strg",
        "ctrl_r": "Strg",
        "control_l": "Strg",
        "control_r": "Strg",
        "alt_l": "Alt",
        "alt_r": "Alt",
        "shift": "Shift",
        "shift_l": "Shift",
        "shift_r": "Shift",
        "cmd": "Cmd",
        "cmd_l": "Cmd",
        "cmd_r": "Cmd",
        "meta_l": "Cmd",
        "meta_r": "Cmd",
    }
    return mapping.get(k, k)


def _key_action_text(k: str) -> str:
    kl = (k or "").strip().lower()
    if kl == "enter":
        return "Drücke Enter, um zu bestätigen."
    if kl == "tab":
        return "Drücke Tab, um zum nächsten Feld zu wechseln."
    if kl == "esc":
        return "Drücke Esc, um zu schließen."
    if kl == "leertaste" or kl == "space":
        return "Drücke die Leertaste."
    if k:
        return f"Drücke {k}."
    return "Drücke die Taste."


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


def _normalize_bounds(bounds: Any) -> Optional[Tuple[int, int, int, int]]:
    if isinstance(bounds, (list, tuple)) and len(bounds) == 4:
        return int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3])
    return None


def _xy_to_hint(x: int, y: int, bounds: Optional[Tuple[int, int, int, int]]) -> str:
    if not bounds:
        return ""
    l, t, r, b = bounds
    w = max(1, r - l)
    h = max(1, b - t)
    rx = (x - l) / w
    ry = (y - t) / h

    def bucket_x(v: float) -> str:
        if v < 1 / 3:
            return "links"
        if v > 2 / 3:
            return "rechts"
        return "mittig"

    def bucket_y(v: float) -> str:
        if v < 1 / 3:
            return "oben"
        if v > 2 / 3:
            return "unten"
        return "mittig"

    bx = bucket_x(rx)
    by = bucket_y(ry)

    if bx == "mittig" and by == "mittig":
        return "in der Mitte"
    if bx == "mittig":
        return f"{by}"
    if by == "mittig":
        return f"{bx}"
    return f"{by} {bx}"


def _pick_monitor_bounds(x: int, y: int, monitors: list[Tuple[int, int, int, int]]) -> Optional[Tuple[int, int, int, int]]:
    for l, t, r, b in monitors:
        if l <= x < r and t <= y < b:
            return (l, t, r, b)
    return monitors[0] if monitors else None


def _extract_monitors_from_data(data: Dict[str, Any]) -> list[Tuple[int, int, int, int]]:
    out: list[Tuple[int, int, int, int]] = []
    raw = data.get("monitors") or data.get("monitor") or []
    if isinstance(raw, list):
        for m in raw:
            if not isinstance(m, dict):
                continue
            if all(k in m for k in ("left", "top", "right", "bottom")):
                out.append((int(m["left"]), int(m["top"]), int(m["right"]), int(m["bottom"])))
                continue
            if all(k in m for k in ("x", "y", "width", "height")):
                l = int(m["x"])
                t = int(m["y"])
                r = l + int(m["width"])
                b = t + int(m["height"])
                out.append((l, t, r, b))
                continue
            if all(k in m for k in ("left", "top", "width", "height")):
                l = int(m["left"])
                t = int(m["top"])
                r = l + int(m["width"])
                b = t + int(m["height"])
                out.append((l, t, r, b))
                continue
    return out


def generate_instruction(event: Dict[str, Any], prev_event: Optional[Dict[str, Any]] = None) -> str:
    kind = (event.get("kind") or "").lower()
    detail = event.get("detail") or ""
    ctx = _ctx(event)
    prefix = (ctx + ": ") if ctx else ""

    if kind == "text_input":
        txt = (event.get("input_text") or "").strip()
        if txt:
            if isinstance(prev_event, dict) and (prev_event.get("kind") or "").lower() == "mouse_click":
                return f'{prefix}Gib „{txt}“ in das ausgewählte Feld ein.'
            return f'{prefix}Gib „{txt}“ ein.'
        return f"{prefix}Gib den Text ein."

    if kind == "mouse_click":
        b = _human_button(detail)
        xy = _extract_xy(detail)
        bounds = _normalize_bounds(event.get("bounds"))
        hint = _xy_to_hint(xy[0], xy[1], bounds) if (xy and bounds) else ""
        if hint:
            return f"{prefix}{b} {hint} auf die markierte Stelle im Screenshot."
        if xy:
            return f"{prefix}{b} auf die markierte Stelle im Screenshot (Position {xy[0]},{xy[1]})."
        return f"{prefix}{b} auf die markierte Stelle im Screenshot."

    if kind == "key_press":
        k = _human_key(detail)
        return f"{prefix}{_key_action_text(k)}"

    if detail.strip():
        return (prefix + detail.strip()).strip()

    return (prefix + "Führe den Schritt aus.").strip()


def enrich_steps_json(data: Dict[str, Any]) -> Dict[str, Any]:
    events = data.get("events") or []
    monitors = _extract_monitors_from_data(data)
    prev: Optional[Dict[str, Any]] = None

    for e in events:
        if not (isinstance(e, dict) and e.get("kind") in ("mouse_click", "key_press", "text_input")):
            prev = e if isinstance(e, dict) else None
            continue

        if (e.get("kind") == "mouse_click") and (not _normalize_bounds(e.get("bounds"))):
            xy = _extract_xy(str(e.get("detail") or ""))
            if xy and monitors:
                b = _pick_monitor_bounds(xy[0], xy[1], monitors)
                if b:
                    e["bounds"] = [b[0], b[1], b[2], b[3]]

        e["instruction"] = generate_instruction(e, prev)
        prev = e

    data["events"] = events
    return data