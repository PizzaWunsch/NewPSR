from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict

from docx import Document
from docx.shared import Inches


def export_docx(out_dir: str, title: str = "Anleitung (PSR-ähnlich)"):
    steps_path = os.path.join(out_dir, "steps.json")
    if not os.path.exists(steps_path):
        raise FileNotFoundError(f"steps.json not found in {out_dir}")

    with open(steps_path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    events = data.get("events", [])
    monitors = {m["index"]: m for m in data.get("monitors", [])}
    delay_ms = int(data.get("screenshot_delay_ms") or 0)

    def mon_label(idx):
        if not idx or idx not in monitors:
            return "Monitor: (unbekannt)"
        m = monitors[idx]
        return f"Monitor {idx} ({m['width']}×{m['height']} @ {m['left']},{m['top']})"

    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(f"Erstellt am {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    doc.add_paragraph(f"Screenshot-Verzögerung: {delay_ms} ms")

    step_no = 0
    for e in events:
        if e.get("kind") in ("mouse_click", "key_press", "note"):
            step_no += 1
            text = e.get("instruction") or e.get("detail") or ""
            doc.add_heading(f"Schritt {step_no}", level=2)
            doc.add_paragraph(f"Zeit: {float(e.get('t', 0.0)):.2f}s")
            if e.get("monitor_index") is not None:
                doc.add_paragraph(mon_label(e.get("monitor_index")))
            doc.add_paragraph(text)

            ss = e.get("screenshot")
            if ss:
                abs_img = os.path.join(out_dir, ss)
                if os.path.exists(abs_img):
                    doc.add_picture(abs_img, width=Inches(6.5))

    out_path = os.path.join(out_dir, "anleitung.docx")
    doc.save(out_path)
    return out_path