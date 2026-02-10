# gui/app.py
from __future__ import annotations

import os
import time
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import multiprocessing as mp
from multiprocessing.connection import Connection
from typing import Optional, Dict, Any

from gui.recorder_process import recorder_worker


class RecorderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PSR-like Recorder")
        self.geometry("680x420")
        self.minsize(600, 360)

        self.var_video = tk.BooleanVar(value=False)
        self.var_fps = tk.IntVar(value=8)
        self.var_format = tk.StringVar(value="html")
        self.var_delay = tk.IntVar(value=250)

        self.worker_proc: Optional[mp.Process] = None
        self.worker_conn: Optional[Connection] = None

        self.out_dir: Optional[str] = None
        self._start_ts: Optional[float] = None

        self._build_ui()

        self.after(150, self._poll_worker)
        self.after(250, self._push_exclude_rect)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._ensure_worker()

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="PSR-ähnliche Aufzeichnung", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 10))

        options = ttk.LabelFrame(root, text="Optionen")
        options.pack(fill="x", pady=8)

        row1 = ttk.Frame(options)
        row1.pack(fill="x", padx=10, pady=(8, 4))

        ttk.Checkbutton(row1, text="Video pro Monitor aufnehmen", variable=self.var_video).pack(side="left")
        ttk.Label(row1, text="FPS:").pack(side="left", padx=(18, 6))
        ttk.Spinbox(row1, from_=3, to=30, textvariable=self.var_fps, width=6).pack(side="left")

        ttk.Label(row1, text="Screenshot-Verzögerung (ms):").pack(side="left", padx=(18, 6))
        ttk.Spinbox(row1, from_=0, to=2000, textvariable=self.var_delay, width=7).pack(side="left")

        row2 = ttk.Frame(options)
        row2.pack(fill="x", padx=10, pady=(4, 10))

        ttk.Label(row2, text="Export:").pack(side="left")
        for fmt, label in [("html", "HTML"), ("docx", "DOCX"), ("pdf", "PDF")]:
            ttk.Radiobutton(row2, text=label, value=fmt, variable=self.var_format).pack(side="left", padx=10)

        self.status = ttk.Label(root, text="Status: bereit")
        self.status.pack(anchor="w", pady=(10, 6))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=10)

        self.btn_start = ttk.Button(btns, text="Start", command=self.start_recording)
        self.btn_stop = ttk.Button(btns, text="Stop", command=self.stop_recording, state="disabled")

        self.btn_start.pack(side="left")
        self.btn_stop.pack(side="left", padx=10)

        ttk.Label(root, text="Klicks innerhalb dieses Fensters werden während der Aufnahme ignoriert.", foreground="#666").pack(anchor="w", pady=(6, 0))

    def _ensure_worker(self):
        if self.worker_proc and self.worker_proc.is_alive() and self.worker_conn:
            return
        try:
            mp.set_start_method("spawn", force=True)
        except RuntimeError:
            pass

        parent_conn, child_conn = mp.Pipe()

        config = {
            "enable_video": bool(self.var_video.get()),
            "video_fps": int(self.var_fps.get()),
            "screenshot_on_keys": ("enter", "tab"),
            "output_format": (self.var_format.get() or "html").lower(),
            "screenshot_delay_ms": int(self.var_delay.get()),
            "record_text_input": True,
        }

        proc = mp.Process(target=recorder_worker, args=(child_conn, config), daemon=True)
        proc.start()

        self.worker_proc = proc
        self.worker_conn = parent_conn
        self.status.config(text="Status: Worker gestartet (bereit)")

    def _restart_worker_with_current_config(self):
        try:
            if self.worker_conn:
                self.worker_conn.send({"type": "quit"})
        except Exception:
            pass

        try:
            if self.worker_proc and self.worker_proc.is_alive():
                self.worker_proc.join(timeout=1.0)
        except Exception:
            pass

        self.worker_conn = None
        self.worker_proc = None
        self._ensure_worker()

    def _send(self, msg: Dict[str, Any]):
        self._ensure_worker()
        if not self.worker_conn:
            messagebox.showerror("Fehler", "Worker-Verbindung fehlt.")
            return
        try:
            self.worker_conn.send(msg)
        except Exception as e:
            messagebox.showerror("Fehler", f"Worker-Kommunikation fehlgeschlagen: {e}")

    def _window_rect(self):
        self.update_idletasks()
        x = int(self.winfo_rootx())
        y = int(self.winfo_rooty())
        w = int(self.winfo_width())
        h = int(self.winfo_height())
        return (x, y, x + w, y + h)

    def _push_exclude_rect(self):
        if self.worker_conn and self._start_ts is not None:
            rect = self._window_rect()
            try:
                self.worker_conn.send({"type": "set_exclude_rect", "rect": rect})
            except Exception:
                pass
        self.after(250, self._push_exclude_rect)

    def _poll_worker(self):
        if self._start_ts:
            elapsed = time.time() - self._start_ts
            base = os.path.basename(self.out_dir) if self.out_dir else "(kein Ordner)"
            self.status.config(text=f"Status: läuft… {elapsed:0.1f}s  Ausgabe: {base}")

        try:
            if self.worker_conn:
                while self.worker_conn.poll():
                    msg = self.worker_conn.recv()
                    self._handle_worker_msg(msg)
        except EOFError:
            self.status.config(text="Status: Worker beendet (EOF).")
        except Exception:
            pass

        self.after(150, self._poll_worker)

    def _handle_worker_msg(self, msg: Dict[str, Any]):
        mtype = msg.get("type")

        if mtype == "ready":
            self.status.config(text="Status: bereit")

        elif mtype == "started":
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            self._start_ts = time.time()
            if self.worker_conn:
                self._send({"type": "set_exclude_rect", "rect": self._window_rect()})

        elif mtype == "stopped":
            self._start_ts = None
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")

            out_path = msg.get("out_path")
            fmt = (msg.get("format") or "html").upper()
            export_error = msg.get("export_error")

            if out_path:
                self.status.config(text=f"Status: gestoppt. {fmt}: {os.path.basename(out_path)}")
                messagebox.showinfo("Fertig", f"Export erstellt ({fmt}):\n{out_path}")
            else:
                self.status.config(text=f"Status: gestoppt. {fmt}: nicht erstellt")
                if export_error:
                    messagebox.showerror("Export-Fehler", export_error)

        elif mtype == "error":
            messagebox.showerror("Fehler", msg.get("message", "Unbekannter Fehler"))

        elif mtype == "fatal":
            trace = msg.get("trace", "")
            self._start_ts = None
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.status.config(text="Status: Worker abgestürzt (fatal).")
            messagebox.showerror("Worker fatal", trace[:4000] or "Fatal error")

    def start_recording(self):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.out_dir = os.path.join(os.getcwd(), f"psr_like_{ts}")
        self._restart_worker_with_current_config()
        self._send({"type": "set_exclude_rect", "rect": self._window_rect()})
        self._send({"type": "start", "out_dir": self.out_dir})

    def stop_recording(self):
        self._send({"type": "stop"})

    def _on_close(self):
        try:
            if self.worker_conn:
                try:
                    self.worker_conn.send({"type": "quit"})
                except Exception:
                    pass
            if self.worker_proc and self.worker_proc.is_alive():
                try:
                    self.worker_proc.join(timeout=1.0)
                except Exception:
                    pass
        finally:
            self.destroy()


if __name__ == "__main__":
    RecorderGUI().mainloop()