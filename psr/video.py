from __future__ import annotations
import threading
import time
import os
from typing import Dict, Optional

import mss
import cv2
import numpy as np

from .models import MonitorInfo


class MultiMonitorVideoWriter:

    def __init__(self, out_dir: str, monitors: list[MonitorInfo], fps: int = 8, enabled: bool = True):
        self.out_dir = out_dir
        self.monitors = monitors
        self.fps = fps
        self.enabled = enabled

        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()

        self._writers: Dict[int, cv2.VideoWriter] = {}
        self._sct = None

    def start(self):
        if not self.enabled:
            return

        os.makedirs(self.out_dir, exist_ok=True)
        self._stop.clear()
        self._sct = mss.mss()

        for m in self.monitors:
            path = os.path.join(self.out_dir, f"monitor_{m.index}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(path, fourcc, self.fps, (m.width, m.height))
            self._writers[m.index] = writer

            t = threading.Thread(target=self._loop_monitor, args=(m,), daemon=True)
            self._threads.append(t)
            t.start()

    def stop(self):
        if not self.enabled:
            return

        self._stop.set()
        for t in self._threads:
            t.join(timeout=3)

        for w in self._writers.values():
            try:
                w.release()
            except Exception:
                pass

        self._writers.clear()
        self._threads.clear()

        if self._sct:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None

    def _loop_monitor(self, m: MonitorInfo):
        assert self._sct is not None
        frame_interval = 1.0 / max(1, self.fps)
        next_t = time.time()

        while not self._stop.is_set():
            now = time.time()
            if now < next_t:
                time.sleep(max(0.0, next_t - now))
                continue
            next_t += frame_interval

            bbox = {"left": m.left, "top": m.top, "width": m.width, "height": m.height}
            shot = self._sct.grab(bbox)
            frame = np.array(shot)  # BGRA
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            self._writers[m.index].write(frame)