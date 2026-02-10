from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet


def export_pdf(out_dir: str, title: str = "Anleitung (PSR-ähnlich)"):
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

    out_path = os.path.join(out_dir, "anleitung.pdf")
    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(f"Erstellt am {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles["Normal"]))
    story.append(Paragraph(f"Screenshot-Verzögerung: {delay_ms} ms", styles["Normal"]))
    story.append(Spacer(1, 0.6 * cm))

    step_no = 0
    max_w = A4[0] - 4 * cm
    max_h = A4[1] - 6 * cm

    for e in events:
        if e.get("kind") in ("mouse_click", "key_press", "note"):
            step_no += 1
            text = e.get("instruction") or e.get("detail") or ""
            story.append(Paragraph(f"Schritt {step_no}", styles["Heading2"]))
            story.append(Paragraph(f"Zeit: {float(e.get('t', 0.0)):.2f}s", styles["Normal"]))
            if e.get("monitor_index") is not None:
                story.append(Paragraph(mon_label(e.get("monitor_index")), styles["Normal"]))
            story.append(Paragraph(text, styles["Normal"]))
            story.append(Spacer(1, 0.3 * cm))

            ss = e.get("screenshot")
            if ss:
                abs_img = os.path.join(out_dir, ss)
                if os.path.exists(abs_img):
                    img = RLImage(abs_img)
                    iw, ih = img.imageWidth, img.imageHeight
                    scale = min(max_w / iw, max_h / ih, 1.0)
                    img.drawWidth = iw * scale
                    img.drawHeight = ih * scale
                    story.append(img)
                    story.append(Spacer(1, 0.6 * cm))

            if step_no % 3 == 0:
                story.append(PageBreak())

    doc.build(story)
    return out_path