# gui/recorder_process.py
from __future__ import annotations

import json
import os
import traceback
from dataclasses import asdict
from typing import Any, Dict, Optional, Tuple

from exporters.html_exporter import export_html
from psr.narrator import enrich_steps_json
from psr.recordings_store import ensure_recordings_root, resolve_recording_dir
from psr.recorder import PSRLikeRecorder


def recorder_worker(conn, config: Dict[str, Any]):
    rec = None
    out_dir: Optional[str] = None
    exclude_rect: Optional[Tuple[int, int, int, int]] = None

    def send(msg: Dict[str, Any]):
        try:
            conn.send(msg)
        except Exception:
            pass

    def inside_exclude(x: int, y: int) -> bool:
        if not exclude_rect:
            return False
        l, t, r, b = exclude_rect
        return l <= x < r and t <= y < b

    def _monitors_to_jsonable():
        if not rec or not getattr(rec, "monitors", None):
            return []
        ms = []
        for m in rec.monitors:
            d = asdict(m) if hasattr(m, "__dict__") or hasattr(m, "__dataclass_fields__") else dict(m)
            if all(k in d for k in ("left", "top", "width", "height")):
                l = int(d["left"])
                t = int(d["top"])
                r = l + int(d["width"])
                b = t + int(d["height"])
                ms.append({"left": l, "top": t, "right": r, "bottom": b})
            elif all(k in d for k in ("x", "y", "width", "height")):
                l = int(d["x"])
                t = int(d["y"])
                r = l + int(d["width"])
                b = t + int(d["height"])
                ms.append({"left": l, "top": t, "right": r, "bottom": b})
            elif all(k in d for k in ("left", "top", "right", "bottom")):
                ms.append({"left": int(d["left"]), "top": int(d["top"]), "right": int(d["right"]), "bottom": int(d["bottom"])})
        return ms

    def apply_narration(_out_dir: str):
        p = os.path.join(_out_dir, "steps.json")
        if not os.path.exists(p):
            return
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data.get("monitors"):
            data["monitors"] = _monitors_to_jsonable()

        data = enrich_steps_json(data)

        events = data.get("events") or []
        prev_kind: Optional[str] = None

        for e in events:
            if not isinstance(e, dict):
                prev_kind = None
                continue

            kind = (e.get("kind") or "").lower()

            if kind == "key_press":
                detail = str(e.get("detail") or "").lower()
                if "enter" in detail and prev_kind == "text_input":
                    e["screenshot"] = None

            prev_kind = kind

        data["events"] = events

        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    try:
        ensure_recordings_root()
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
                    send({"type": "error", "message": "Recorder already running."})
                    continue

                raw_out_dir = cmd.get("out_dir")
                out_dir = resolve_recording_dir(raw_out_dir)
                os.makedirs(out_dir, exist_ok=True)

                rec = PSRLikeRecorder(
                    out_dir=out_dir,
                    screenshot_on_click=True,
                    screenshot_on_keys=tuple(config.get("screenshot_on_keys", ("tab",))),
                    enable_video=bool(config.get("enable_video", False)),
                    video_fps=int(config.get("video_fps", 8)),
                    screenshot_delay_ms=int(config.get("screenshot_delay_ms", 0)),
                    record_text_input=bool(config.get("record_text_input", True)),
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
                            "record_text_input": rec.record_text_input,
                        }
                    )
                except Exception as e:
                    rec = None
                    send({"type": "error", "message": f"Start failed: {e}"})
                continue

            if ctype == "stop":
                if not rec or not rec.running:
                    send({"type": "error", "message": "Recorder not running."})
                    continue

                try:
                    rec.stop()
                except Exception as e:
                    send({"type": "error", "message": f"Stop failed: {e}"})
                    continue

                try:
                    if out_dir:
                        apply_narration(out_dir)
                except Exception as e:
                    send({"type": "error", "message": f"Narration failed: {e}"})

                out_path = None
                export_error = None
                try:
                    if out_dir:
                        out_path = export_html(out_dir)
                except Exception as e:
                    export_error = str(e)

                send(
                    {
                        "type": "stopped",
                        "out_dir": out_dir,
                        "out_path": out_path,
                        "format": "html",
                        "export_error": export_error,
                    }
                )
                continue

            if ctype == "ping":
                send({"type": "pong", "running": bool(rec and rec.running), "out_dir": out_dir})
                continue

            send({"type": "error", "message": f"Unknown command: {ctype}"})

    except EOFError:
        pass
    except Exception:
        send({"type": "fatal", "trace": traceback.format_exc()})
    finally:
        try:
            conn.close()
        except Exception:
            pass