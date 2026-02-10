# exporters/pdf_exporter.py
from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT


def export_pdf(out_dir: str, title: str = "Schritt-für-Schritt Anleitung"):
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
            return None
        m = monitors[idx]
        return f"Monitor {idx} ({m['width']}×{m['height']})"

    out_path = os.path.join(out_dir, "anleitung.pdf")
    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("t", parent=styles["Title"], fontSize=18, leading=22, alignment=TA_LEFT)
    meta_style = ParagraphStyle("m", parent=styles["Normal"], fontSize=9.5, leading=12.5, textColor="#444444")
    step_style = ParagraphStyle("s", parent=styles["Normal"], fontSize=11.5, leading=15, spaceAfter=6)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9.5, leading=12.5, textColor="#555555")

    created = datetime.now().strftime("%d.%m.%Y %H:%M")

    story = []
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(f"Erstellt: {created}  ·  Screenshot-Verzögerung: {delay_ms} ms", meta_style))
    story.append(Spacer(1, 0.7 * cm))

    max_w = A4[0] - 4 * cm
    max_h = A4[1] - 6.5 * cm

    step_no = 0
    blocks = 0

    for e in events:
        if e.get("kind") in ("mouse_click", "key_press", "text_input"):
            text = (e.get("instruction") or e.get("detail") or "").strip()
            if not text:
                continue
            step_no += 1

            parts = []
            parts.append(Paragraph(f"<b>{step_no}. {text}</b>", step_style))

            ml = mon_label(e.get("monitor_index"))
            if ml:
                parts.append(Paragraph(ml, sub_style))
                parts.append(Spacer(1, 0.15 * cm))

            ss = e.get("screenshot")
            if ss:
                abs_img = os.path.join(out_dir, ss)
                if os.path.exists(abs_img):
                    img = RLImage(abs_img)
                    iw, ih = img.imageWidth, img.imageHeight
                    scale = min(max_w / iw, max_h / ih, 1.0)
                    img.drawWidth = iw * scale
                    img.drawHeight = ih * scale
                    parts.append(img)

            parts.append(Spacer(1, 0.55 * cm))
            story.append(KeepTogether(parts))

            blocks += 1
            if blocks % 3 == 0:
                story.append(PageBreak())

    if step_no == 0:
        story.append(Paragraph("Keine Schritte aufgezeichnet.", step_style))

    doc.build(story)
    return out_path