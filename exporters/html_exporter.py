# exporters/html_exporter.py
from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict


def export_html(out_dir: str, title: str = "Schritt-für-Schritt Anleitung"):
    steps_path = os.path.join(out_dir, "steps.json")
    if not os.path.exists(steps_path):
        raise FileNotFoundError(f"steps.json not found in {out_dir}")

    with open(steps_path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    events = data.get("events", [])
    monitors = {m["index"]: m for m in data.get("monitors", [])}
    video_enabled = bool(data.get("video_enabled"))
    video_dir = data.get("video_dir")
    delay_ms = int(data.get("screenshot_delay_ms") or 0)

    def mon_label(idx: int | None) -> str:
        if not idx or idx not in monitors:
            return ""
        m = monitors[idx]
        return f"Monitor {idx} ({m['width']}×{m['height']})"

    steps = []
    step_no = 0
    for e in events:
        if e.get("kind") in ("mouse_click", "key_press", "text_input"):
            text = (e.get("instruction") or e.get("detail") or "").strip()
            if not text:
                continue
            step_no += 1

            meta = []
            ml = mon_label(e.get("monitor_index"))
            if ml:
                meta.append(ml)
            meta_html = f"<div class='meta'>{' · '.join(meta)}</div>" if meta else ""

            img_html = ""
            if e.get("screenshot"):
                img_html = f"<div class='shot'><img src='{e['screenshot']}' alt='Schritt {step_no}'></div>"

            steps.append(
                f"""
                <section class="step">
                  <div class="step-h">
                    <div class="badge">{step_no}</div>
                    <div class="step-t">
                      <div class="title">{text}</div>
                      {meta_html}
                    </div>
                  </div>
                  {img_html}
                </section>
                """
            )

    video_block = ""
    if video_enabled and video_dir:
        parts = []
        for idx in sorted(monitors.keys()):
            mp4 = os.path.join(out_dir, video_dir, f"monitor_{idx}.mp4")
            if os.path.exists(mp4):
                rel = os.path.relpath(mp4, out_dir)
                label = mon_label(idx) or f"Monitor {idx}"
                parts.append(
                    f"""
                    <div class="video">
                      <div class="vlabel">{label}</div>
                      <video controls preload="metadata">
                        <source src="{rel}" type="video/mp4">
                      </video>
                    </div>
                    """
                )
        if parts:
            video_block = f"""
            <h2>Aufzeichnung (optional)</h2>
            <div class="videos">{''.join(parts)}</div>
            """

    created = datetime.now().strftime("%d.%m.%Y %H:%M")
    html_path = os.path.join(out_dir, "anleitung.html")
    html = f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0b0c10;
      --text: #e9e9ee;
      --muted: #b5b7c2;
      --line: rgba(255,255,255,.10);
      --accent: #4f8cff;
    }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
      background: linear-gradient(180deg, #0b0c10 0%, #0e1020 100%);
      color: var(--text);
    }}
    .wrap {{
      max-width: 980px;
      margin: 0 auto;
      padding: 28px 18px 60px;
    }}
    header {{
      background: rgba(255,255,255,.03);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px 18px 16px;
      box-shadow: 0 12px 40px rgba(0,0,0,.35);
    }}
    h1 {{
      margin: 0;
      font-size: 1.6rem;
      letter-spacing: .2px;
    }}
    .sub {{
      margin-top: 8px;
      color: var(--muted);
      font-size: .95rem;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .pill {{
      display: inline-flex;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.04);
      padding: 5px 10px;
      border-radius: 999px;
      gap: 8px;
      align-items: center;
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 1.15rem;
      color: #f0f2ff;
    }}
    .steps {{
      display: grid;
      gap: 14px;
    }}
    .step {{
      background: rgba(255,255,255,.03);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      box-shadow: 0 10px 30px rgba(0,0,0,.25);
    }}
    .step-h {{
      display: grid;
      grid-template-columns: 38px 1fr;
      gap: 12px;
      align-items: start;
    }}
    .badge {{
      width: 34px;
      height: 34px;
      border-radius: 12px;
      background: rgba(79,140,255,.16);
      border: 1px solid rgba(79,140,255,.35);
      color: #dbe6ff;
      display: grid;
      place-items: center;
      font-weight: 700;
    }}
    .title {{
      font-size: 1.03rem;
      line-height: 1.25rem;
      white-space: pre-wrap;
    }}
    .meta {{
      margin-top: 6px;
      color: var(--muted);
      font-size: .92rem;
    }}
    .shot {{
      margin-top: 12px;
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.02);
    }}
    .shot img {{
      width: 100%;
      display: block;
    }}
    .videos {{
      display: grid;
      gap: 14px;
    }}
    .video {{
      background: rgba(255,255,255,.03);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
    }}
    .vlabel {{
      color: var(--muted);
      font-size: .95rem;
      margin-bottom: 8px;
    }}
    video {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: #000;
    }}
    footer {{
      margin-top: 26px;
      color: var(--muted);
      font-size: .9rem;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{title}</h1>
      <div class="sub">
        <span class="pill">Erstellt: {created}</span>
        <span class="pill">Screenshot-Verzögerung: {delay_ms} ms</span>
        <span class="pill">Schritte: {len(steps)}</span>
      </div>
    </header>

    {video_block}

    <h2>Schritte</h2>
    <div class="steps">
      {''.join(steps) if steps else "<div class='step'><div class='title'>Keine Schritte aufgezeichnet.</div></div>"}
    </div>

    <footer>
      <span>https://github.com/PizzaWunsch/NewPSR</span>
    </footer>
  </div>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return html_path