from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from psr.paths import recordings_root_dir


@dataclass
class RecordingItem:
    name: str
    path: str
    created_ts: float
    has_steps: bool
    has_html: bool


def ensure_recordings_root() -> str:
    root = recordings_root_dir()
    os.makedirs(root, exist_ok=True)
    return root


def _safe_name(name: str) -> str:
    n = (name or "").strip()
    n = re.sub(r"[^\w\s\-.()äöüÄÖÜß]", "", n, flags=re.UNICODE)
    n = re.sub(r"\s+", " ", n, flags=re.UNICODE).strip()
    return n[:80] if n else ""


def default_recording_name() -> str:
    return "Recording " + datetime.now().strftime("%Y-%m-%d %H-%M-%S")


def create_recording_dir(name: Optional[str] = None) -> str:
    root = ensure_recordings_root()
    base = _safe_name(name) or default_recording_name()
    candidate = base
    i = 2
    while os.path.exists(os.path.join(root, candidate)):
        candidate = f"{base} ({i})"
        i += 1
    p = os.path.join(root, candidate)
    os.makedirs(p, exist_ok=True)
    meta_path = os.path.join(p, "recording.meta.json")
    if not os.path.exists(meta_path):
        meta = {"name": candidate, "created": datetime.now().isoformat(timespec="seconds")}
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    return p


def resolve_recording_dir(raw: Any) -> str:
    root = ensure_recordings_root()

    if isinstance(raw, str) and raw.strip():
        p = raw.strip()

        if os.path.isabs(p):
            if os.path.isdir(p):
                return p
            base = os.path.basename(p.rstrip("/\\"))
            return create_recording_dir(base)

        if os.path.sep in p or (os.path.altsep and os.path.altsep in p):
            p2 = os.path.abspath(p)
            if os.path.isdir(p2):
                return p2
            base = os.path.basename(p2.rstrip("/\\"))
            return create_recording_dir(base)

        candidate = os.path.join(root, p)
        if os.path.isdir(candidate):
            return candidate
        return create_recording_dir(p)

    return create_recording_dir()


def list_recordings() -> List[RecordingItem]:
    root = ensure_recordings_root()
    items: List[RecordingItem] = []
    for entry in os.listdir(root):
        p = os.path.join(root, entry)
        if not os.path.isdir(p):
            continue
        meta_path = os.path.join(p, "recording.meta.json")
        name = entry
        created_ts = os.path.getmtime(p)
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if isinstance(meta, dict) and meta.get("name"):
                    name = str(meta.get("name"))
            except Exception:
                pass
        has_steps = os.path.exists(os.path.join(p, "steps.json"))
        has_html = os.path.exists(os.path.join(p, "anleitung.html"))
        items.append(RecordingItem(name=name, path=p, created_ts=created_ts, has_steps=has_steps, has_html=has_html))
    items.sort(key=lambda x: x.created_ts, reverse=True)
    return items


def rename_recording(old_path: str, new_name: str) -> str:
    root = ensure_recordings_root()
    new_base = _safe_name(new_name)
    if not new_base:
        raise ValueError("Ungültiger Name")

    new_path = os.path.join(root, new_base)
    if os.path.abspath(old_path) == os.path.abspath(new_path):
        _write_meta(old_path, new_base)
        return old_path

    candidate = new_base
    i = 2
    while os.path.exists(os.path.join(root, candidate)):
        candidate = f"{new_base} ({i})"
        i += 1

    new_path = os.path.join(root, candidate)
    shutil.move(old_path, new_path)
    _write_meta(new_path, candidate)
    return new_path


def delete_recording(path: str) -> None:
    if not os.path.isdir(path):
        return
    shutil.rmtree(path, ignore_errors=True)


def _write_meta(path: str, name: str) -> None:
    meta_path = os.path.join(path, "recording.meta.json")
    meta = {"name": name, "updated": datetime.now().isoformat(timespec="seconds")}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                old = json.load(f)
            if isinstance(old, dict):
                meta = {**old, **meta}
        except Exception:
            pass
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)