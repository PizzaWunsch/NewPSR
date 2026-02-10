# psr/recorder.py
from __future__ import annotations

import os
import time
import json
from datetime import datetime
from typing import Optional, Tuple, List, Set

import mss
from PIL import Image
from pynput import mouse, keyboard

from .models import StepEvent, MonitorInfo
from .monitor import list_monitors, find_monitor_for_point
from .annotate import mark_click
from .video import MultiMonitorVideoWriter


class PSRLikeRecorder:
    def __init__(
        self,
        out_dir: str,
        screenshot_on_click: bool = True,
        screenshot_on_keys: Tuple[str, ...] = ("enter", "tab"),
        enable_video: bool = False,
        video_fps: int = 8,
        screenshot_delay_ms: int = 0,
        record_text_input: bool = True,
    ):
        self.out_dir = out_dir
        self.img_dir = os.path.join(out_dir, "images")
        self.video_dir = os.path.join(out_dir, "video")

        os.makedirs(self.img_dir, exist_ok=True)

        self.monitors: List[MonitorInfo] = list_monitors()
        self.events: List[StepEvent] = []

        self.screenshot_on_click = screenshot_on_click
        self.screenshot_on_keys: Set[str] = set(screenshot_on_keys)

        self.enable_video = enable_video
        self.video_fps = video_fps
        self.screenshot_delay_ms = max(0, int(screenshot_delay_ms))
        self.record_text_input = bool(record_text_input)

        self.running = False
        self._start_time: Optional[float] = None

        self._sct = mss.mss()
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None

        self._video = MultiMonitorVideoWriter(self.video_dir, self.monitors, fps=self.video_fps, enabled=self.enable_video)

        self._text_buf: str = ""
        self._last_type_ts: float = 0.0

    def _now_rel(self) -> float:
        assert self._start_time is not None
        return time.time() - self._start_time

    def start(self):
        if self.running:
            return
        os.makedirs(self.out_dir, exist_ok=True)

        self.running = True
        self._start_time = time.time()
        self._text_buf = ""
        self._last_type_ts = 0.0

        self.events.append(StepEvent(0.0, "start", "Recording started"))

        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self._mouse_listener.start()
        self._keyboard_listener.start()

        self._video.start()

    def stop(self):
        if not self.running:
            return
        self._flush_text_input(reason="stop", take_screenshot=False, monitor_for_screenshot=None)
        self.running = False
        self.events.append(StepEvent(self._now_rel(), "stop", "Recording stopped"))

        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()

        self._video.stop()
        self._save_steps_json()

    def _save_steps_json(self):
        path = os.path.join(self.out_dir, "steps.json")
        payload = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "monitors": [m.as_dict() for m in self.monitors],
            "events": [e.__dict__ for e in self.events],
            "video_enabled": self.enable_video,
            "video_dir": "video" if self.enable_video else None,
            "screenshot_delay_ms": self.screenshot_delay_ms,
            "record_text_input": self.record_text_input,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _capture_monitor_screenshot(
            self,
            mon: MonitorInfo,
            rel_xy: Optional[Tuple[int, int]],
            delay_ms: int = 0,
    ) -> str:
        if delay_ms and delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"m{mon.index}_{ts}.png"
        abs_path = os.path.join(self.img_dir, filename)

        bbox = {
            "left": mon.left,
            "top": mon.top,
            "width": mon.width,
            "height": mon.height,
        }

        import mss
        with mss.mss() as sct:
            shot = sct.grab(bbox)

        img = Image.frombytes("RGB", shot.size, shot.rgb)
        img = mark_click(img, rel_xy)
        img.save(abs_path)

        return os.path.relpath(abs_path, self.out_dir)

    def _capture_primary_no_marker(self) -> Optional[str]:
        if not self.monitors:
            return None
        mon = self.monitors[0]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"m{mon.index}_text_{ts}.png"
        abs_path = os.path.join(self.img_dir, filename)

        if self.screenshot_delay_ms and self.screenshot_delay_ms > 0:
            time.sleep(self.screenshot_delay_ms / 1000.0)

        bbox = {"left": mon.left, "top": mon.top, "width": mon.width, "height": mon.height}
        shot = self._sct.grab(bbox)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        img.save(abs_path)
        return os.path.relpath(abs_path, self.out_dir)

    def _flush_text_input(self, reason: str, take_screenshot: bool, monitor_for_screenshot: Optional[MonitorInfo]):
        if not self.record_text_input:
            self._text_buf = ""
            return
        txt = self._text_buf
        if not txt:
            return
        txt = txt.replace("\r", "").replace("\n", "")
        if not txt:
            self._text_buf = ""
            return

        ss = None
        if take_screenshot:
            if monitor_for_screenshot:
                ss = self._capture_monitor_screenshot(monitor_for_screenshot, rel_xy=None, delay_ms=self.screenshot_delay_ms)
            else:
                ss = self._capture_primary_no_marker()

        self.events.append(
            StepEvent(
                t=self._now_rel(),
                kind="text_input",
                detail=f"Text eingegeben ({reason})",
                screenshot=ss,
                input_text=txt,
            )
        )
        self._text_buf = ""

    def _on_click(self, x, y, button, pressed):
        if not self.running or not pressed:
            return

        found = find_monitor_for_point(self.monitors, int(x), int(y))
        mon = found[0] if found else None
        rel_x, rel_y = (found[1], found[2]) if found else (None, None)

        self._flush_text_input(reason="focus_change", take_screenshot=False, monitor_for_screenshot=None)

        ss = None
        if self.screenshot_on_click and mon:
            ss = self._capture_monitor_screenshot(mon, (rel_x, rel_y), delay_ms=self.screenshot_delay_ms)

        detail = f"Click {button} at ({int(x)},{int(y)})"
        self.events.append(
            StepEvent(
                t=self._now_rel(),
                kind="mouse_click",
                detail=detail,
                monitor_index=mon.index if mon else None,
                x=int(x),
                y=int(y),
                rel_x=rel_x if mon else None,
                rel_y=rel_y if mon else None,
                screenshot=ss,
            )
        )

    def _append_char(self, ch: str):
        self._text_buf += ch
        self._last_type_ts = time.time()

    def _backspace(self):
        if self._text_buf:
            self._text_buf = self._text_buf[:-1]
        self._last_type_ts = time.time()

    def _on_press(self, key):
        if not self.running:
            return

        try:
            ch = key.char
        except AttributeError:
            ch = None

        if ch is not None:
            if self.record_text_input and len(ch) == 1 and ch.isprintable():
                self._append_char(ch)
            return

        k = str(key).replace("Key.", "").lower()

        if k == "esc":
            self.stop()
            return False

        if self.record_text_input:
            if k == "space":
                self._append_char(" ")
                return
            if k == "backspace":
                self._backspace()
                return
            if k == "enter":
                self._flush_text_input(reason="enter", take_screenshot=True,
                                       monitor_for_screenshot=self.monitors[0] if self.monitors else None)
                return
            if k == "tab":
                self._flush_text_input(reason="tab", take_screenshot=True,
                                       monitor_for_screenshot=self.monitors[0] if self.monitors else None)

        ss = None
        if k in self.screenshot_on_keys and self.monitors:
            ss = self._capture_monitor_screenshot(self.monitors[0], rel_xy=None, delay_ms=self.screenshot_delay_ms)

        important = (k in self.screenshot_on_keys) or (k in ("ctrl_l", "ctrl_r", "alt_l", "alt_r"))
        if important:
            self.events.append(StepEvent(self._now_rel(), "key_press", f"Key: {k}", screenshot=ss))