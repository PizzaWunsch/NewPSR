# psr/video.py
from __future__ import annotations

import os
import threading
import time
from typing import Dict, Optional

import cv2
import mss
import numpy as np

from .models import MonitorInfo


class MultiMonitorVideoWriter:


    def __init__(self, out_dir: str, monitors: list[MonitorInfo], fps: int = 24, enabled: bool = True):
        self.out_dir = out_dir
        self.monitors = monitors
        self.fps = int(fps) if fps and fps > 0 else 24
        self.enabled = bool(enabled)

        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()

        self._writers: Dict[int, cv2.VideoWriter] = {}
        self._sct: Optional[mss.mss] = None

        self._max_catchup_frames = 30

    def start(self):
        if not self.enabled:
            return

        os.makedirs(self.out_dir, exist_ok=True)
        self._stop.clear()

        self._sct = mss.mss()

        self._writers.clear()
        self._threads.clear()

        for m in self.monitors:
            path = os.path.join(self.out_dir, f"monitor_{m.index}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(path, fourcc, float(self.fps), (int(m.width), int(m.height)))
            if not writer.isOpened():
                raise RuntimeError(f"VideoWriter konnte nicht geöffnet werden: {path}")

            self._writers[int(m.index)] = writer

            t = threading.Thread(target=self._loop_monitor, args=(m,), daemon=True)
            self._threads.append(t)
            t.start()

    def stop(self):
        if not self.enabled:
            return

        self._stop.set()
        for t in self._threads:
            t.join(timeout=3)

        for w in list(self._writers.values()):
            try:
                w.release()
            except Exception:
                pass

        self._writers.clear()
        self._threads.clear()

        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None

    def _loop_monitor(self, m: MonitorInfo):
        interval = 1.0 / max(1, self.fps)
        start_t = time.perf_counter()
        written_frames = 0

        idx = int(m.index)
        bbox = {"left": int(m.left), "top": int(m.top), "width": int(m.width), "height": int(m.height)}

        assert self._sct is not None

        last_frame: Optional[np.ndarray] = None

        while not self._stop.is_set():
            now = time.perf_counter()
            target_frames = int((now - start_t) / interval) + 1

            if target_frames - written_frames > self._max_catchup_frames:
                written_frames = target_frames - self._max_catchup_frames

            if written_frames >= target_frames:
                next_t = start_t + (written_frames + 1) * interval
                sleep_s = max(0.0, next_t - time.perf_counter())
                if sleep_s > 0:
                    time.sleep(min(0.01, sleep_s))
                continue

            try:
                shot = self._sct.grab(bbox)  # BGRA
                frame = np.array(shot, dtype=np.uint8)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                last_frame = frame
            except Exception:
                frame = last_frame

            if frame is None:
                time.sleep(0.01)
                continue

            w = self._writers.get(idx)
            if w is None:
                return

            while written_frames < target_frames and not self._stop.is_set():
                w.write(frame)
                written_frames += 1