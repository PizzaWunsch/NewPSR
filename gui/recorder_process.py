from __future__ import annotations

import os
import json
import traceback
from dataclasses import asdict
from typing import Any, Dict, Optional, Tuple

from psr.recorder import PSRLikeRecorder
from psr.narrator import enrich_steps_json
from exporters.html_exporter import export_html
from exporters.docx_exporter import export_docx
from exporters.pdf_exporter import export_pdf


def recorder_worker(conn, config: Dict[str, Any]):
    rec = None
    out_dir = None
    exclude_rect: Optional[Tuple[int, int, int, int]] = None

    def send(msg: Dict[str, Any]):
        try:
            conn.send(msg)
        except Exception:
            pass

    def inside_exclude(x: int, y: int) -> bool:
        nonlocal exclude_rect
        if not exclude_rect:
            return False
        l, t, r, b = exclude_rect
        return l <= x < r and t <= y < b

    def apply_narration(out_dir: str):
        p = os.path.join(out_dir, "steps.json")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = enrich_steps_json(data)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def do_export(fmt: str, out_dir: str):
        fmt = (fmt or "html").lower()
        if fmt == "html":
            return export_html(out_dir)
        if fmt == "docx":
            return export_docx(out_dir)
        if fmt == "pdf":
            return export_pdf(out_dir)
        return export_html(out_dir)

    try:
        send({"type": "ready"})
        while True:
            cmd = conn.recv()
            ctype = cmd.get("type")

            if ctype == "quit":
                try:
                    if rec and rec.running:
                        rec.stop()
                except Exception:
                    pass
                send({"type": "quit_ack"})
                break

            if ctype == "set_exclude_rect":
                rect = cmd.get("rect")
                if isinstance(rect, (list, tuple)) and len(rect) == 4:
                    exclude_rect = (int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))
                continue

            if ctype == "start":
                if rec and rec.running:
                    send({"type": "error", "message": "Recorder läuft bereits."})
                    continue

                out_dir = cmd["out_dir"]
                os.makedirs(out_dir, exist_ok=True)

                rec = PSRLikeRecorder(
                    out_dir=out_dir,
                    screenshot_on_click=True,
                    screenshot_on_keys=tuple(config.get("screenshot_on_keys", ("enter", "tab"))),
                    enable_video=bool(config.get("enable_video", False)),
                    video_fps=int(config.get("video_fps", 8)),
                    screenshot_delay_ms=int(config.get("screenshot_delay_ms", 0)),
                )

                original_on_click = rec._on_click

                def patched_on_click(x, y, button, pressed):
                    if pressed and inside_exclude(int(x), int(y)):
                        return
                    return original_on_click(x, y, button, pressed)

                rec._on_click = patched_on_click

                try:
                    rec.start()
                    send(
                        {
                            "type": "started",
                            "out_dir": out_dir,
                            "monitors": [asdict(m) for m in rec.monitors],
                            "video": rec.enable_video,
                            "delay_ms": rec.screenshot_delay_ms,
                        }
                    )
                except Exception as e:
                    rec = None
                    send({"type": "error", "message": f"Start fehlgeschlagen: {e}"})

            elif ctype == "stop":
                if not rec or not rec.running:
                    send({"type": "error", "message": "Recorder läuft nicht."})
                    continue

                try:
                    rec.stop()
                except Exception as e:
                    send({"type": "error", "message": f"Stop fehlgeschlagen: {e}"})
                    continue

                fmt = (config.get("output_format") or "html").lower()
                try:
                    apply_narration(out_dir)
                    out_path = do_export(fmt, out_dir)
                    send({"type": "stopped", "out_dir": out_dir, "out_path": out_path, "format": fmt})
                except Exception as e:
                    send({"type": "stopped", "out_dir": out_dir, "out_path": None, "format": fmt, "export_error": str(e)})

            elif ctype == "note":
                if not rec or not rec.running:
                    send({"type": "error", "message": "Recorder läuft nicht."})
                    continue
                text = cmd.get("text", "").strip() or "(Notiz ohne Text)"
                try:
                    rec.add_note(text, with_screenshot=True)
                    send({"type": "note_ok"})
                except Exception as e:
                    send({"type": "error", "message": f"Notiz fehlgeschlagen: {e}"})

            elif ctype == "ping":
                send({"type": "pong", "running": bool(rec and rec.running), "out_dir": out_dir})

            else:
                send({"type": "error", "message": f"Unbekanntes Kommando: {ctype}"})

    except EOFError:
        pass
    except Exception:
        send({"type": "fatal", "trace": traceback.format_exc()})
    finally:
        try:
            conn.close()
        except Exception:
            pass