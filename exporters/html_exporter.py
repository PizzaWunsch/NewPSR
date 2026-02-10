from __future__ import annotations
import os
import json
from datetime import datetime
from typing import Any, Dict


def export_html(out_dir: str, title: str = "Anleitung (PSR-ähnlich)"):
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
            return "Monitor: (unbekannt)"
        m = monitors[idx]
        return f"Monitor {idx} ({m['width']}×{m['height']} @ {m['left']},{m['top']})"

    items = []
    step_no = 0
    for e in events:
        if e.get("kind") in ("mouse_click", "key_press", "note"):
            step_no += 1
            text = e.get("instruction") or e.get("detail") or ""
            img_html = ""
            if e.get("screenshot"):
                img_html = f'<div class="img"><img src="{e["screenshot"]}" alt="Step {step_no}"></div>'

            mtxt = ""
            if e.get("monitor_index") is not None:
                mtxt = f'<div class="mon">{mon_label(e.get("monitor_index"))}</div>'

            items.append(
                f"""
                <div class="step">
                  <div class="meta">
                    <div class="nr">Schritt {step_no}</div>
                    <div class="time">{float(e.get("t", 0.0)):0.2f}s</div>
                  </div>
                  {mtxt}
                  <div class="text">{text}</div>
                  {img_html}
                </div>
                """
            )

    video_block = ""
    if video_enabled and video_dir:
        parts = []
        for idx in sorted(monitors.keys()):
            mp4 = os.path.join(out_dir, video_dir, f"monitor_{idx}.mp4")
            if os.path.exists(mp4):
                rel = os.path.relpath(mp4, out_dir)
                parts.append(
                    f"""
                    <div class="video">
                      <div class="mon">{mon_label(idx)}</div>
                      <video controls>
                        <source src="{rel}" type="video/mp4">
                      </video>
                    </div>
                    """
                )
        if parts:
            video_block = f"<h2>Screenrecordings</h2>{''.join(parts)}"

    html_path = os.path.join(out_dir, "anleitung.html")
    html = f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; color:#111; }}
    h1 {{ margin: 0 0 8px; }}
    .sub {{ color:#555; margin-bottom: 20px; }}
    .step {{ border:1px solid #e6e6e6; border-radius:16px; padding:16px; margin:14px 0; }}
    .meta {{ display:flex; gap:12px; align-items:baseline; }}
    .nr {{ font-weight:700; }}
    .time {{ color:#666; font-size: 0.9rem; }}
    .mon {{ color:#444; font-size:0.95rem; margin-top:6px; }}
    .text {{ margin:10px 0 12px; font-size: 1rem; }}
    .img img {{ max-width:100%; border-radius:12px; border:1px solid #ddd; }}
    .video video {{ max-width:100%; border:1px solid #ddd; border-radius:12px; }}
    .video {{ margin: 12px 0 18px; }}
    code {{ background:#f4f4f4; padding:2px 6px; border-radius:8px; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="sub">Erstellt am {datetime.now().strftime("%d.%m.%Y %H:%M")}. Screenshot-Verzögerung: <code>{delay_ms} ms</code></div>
  {video_block}
  <h2>Schritte</h2>
  {''.join(items) if items else "<p>Keine Schritte aufgezeichnet.</p>"}
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return html_path