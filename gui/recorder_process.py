from __future__ import annotations

import os
import traceback
from dataclasses import asdict
from typing import Any, Dict

from psr.recorder import PSRLikeRecorder
from exporters.html_exporter import export_html


def recorder_worker(conn, config: Dict[str, Any]):
    rec = None
    out_dir = None

    def send(msg: Dict[str, Any]):
        try:
            conn.send(msg)
        except Exception:
            pass

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
                )

                try:
                    rec.start()
                    send(
                        {
                            "type": "started",
                            "out_dir": out_dir,
                            "monitors": [asdict(m) for m in rec.monitors],
                            "video": rec.enable_video,
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

                try:
                    html_path = export_html(out_dir)
                    send({"type": "stopped", "out_dir": out_dir, "html_path": html_path})
                except Exception as e:
                    send({"type": "stopped", "out_dir": out_dir, "html_path": None, "export_error": str(e)})

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