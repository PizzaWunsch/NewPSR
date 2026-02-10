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
    """
    Stabil: GUI (Tkinter) im Main-Prozess, Recorder in separatem Prozess.
    Verhindert SIGTRAP-Crashes durch Tkinter+pynput+mss in einem Prozess.
    """

    def __init__(self):
        super().__init__()
        self.title("PSR-like Recorder")
        self.geometry("600x380")
        self.minsize(540, 320)

        self.var_video = tk.BooleanVar(value=False)
        self.var_fps = tk.IntVar(value=8)

        self.worker_proc: Optional[mp.Process] = None
        self.worker_conn: Optional[Connection] = None

        self.out_dir: Optional[str] = None
        self._start_ts: Optional[float] = None

        self._build_ui()

        self.after(150, self._poll_worker)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._ensure_worker()


    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="PSR-ähnliche Aufzeichnung", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        options = ttk.LabelFrame(root, text="Optionen")
        options.pack(fill="x", pady=8)

        row = ttk.Frame(options)
        row.pack(fill="x", padx=10, pady=8)

        ttk.Checkbutton(row, text="Video pro Monitor aufnehmen", variable=self.var_video).pack(side="left")
        ttk.Label(row, text="FPS:").pack(side="left", padx=(18, 6))
        ttk.Spinbox(row, from_=3, to=30, textvariable=self.var_fps, width=6).pack(side="left")

        self.status = ttk.Label(root, text="Status: bereit")
        self.status.pack(anchor="w", pady=(10, 6))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=10)

        self.btn_start = ttk.Button(btns, text="Start", command=self.start_recording)
        self.btn_stop = ttk.Button(btns, text="Stop", command=self.stop_recording, state="disabled")
        self.btn_note = ttk.Button(btns, text="Notiz + Screenshot", command=self.add_note, state="disabled")

        self.btn_start.pack(side="left")
        self.btn_stop.pack(side="left", padx=10)
        self.btn_note.pack(side="left")

        note_frame = ttk.LabelFrame(root, text="Notiztext")
        note_frame.pack(fill="both", expand=True, pady=8)

        self.note_text = tk.Text(note_frame, height=6)
        self.note_text.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            root,
            text="Hinweis: ESC stoppt im Recorder-Prozess (wenn Hook stabil läuft).",
            foreground="#666",
        ).pack(anchor="w", pady=(6, 0))


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
        }

        proc = mp.Process(target=recorder_worker, args=(child_conn, config), daemon=True)
        proc.start()

        self.worker_proc = proc
        self.worker_conn = parent_conn

        self.status.config(text="Status: Worker gestartet (bereit)")

    def _send(self, msg: Dict[str, Any]):
        self._ensure_worker()
        if not self.worker_conn:
            messagebox.showerror("Fehler", "Worker-Verbindung fehlt.")
            return
        try:
            self.worker_conn.send(msg)
        except Exception as e:
            messagebox.showerror("Fehler", f"Worker-Kommunikation fehlgeschlagen: {e}")

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
            self.btn_note.config(state="normal")
            self._start_ts = time.time()
            self.status.config(text=f"Status: läuft… Ausgabe: {os.path.basename(self.out_dir)}")

        elif mtype == "stopped":
            self._start_ts = None
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.btn_note.config(state="disabled")

            html_path = msg.get("html_path")
            export_error = msg.get("export_error")
            if html_path:
                self.status.config(text=f"Status: gestoppt. HTML: {os.path.basename(html_path)}")
                messagebox.showinfo("Fertig", f"Anleitung erstellt:\n{html_path}")
            else:
                self.status.config(text="Status: gestoppt. HTML: nicht erstellt")
                if export_error:
                    messagebox.showerror("Export-Fehler", export_error)

        elif mtype == "note_ok":
            pass

        elif mtype == "error":
            messagebox.showerror("Fehler", msg.get("message", "Unbekannter Fehler"))

        elif mtype == "fatal":
            trace = msg.get("trace", "")
            self._start_ts = None
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.btn_note.config(state="disabled")
            self.status.config(text="Status: Worker abgestürzt (fatal).")
            messagebox.showerror("Worker fatal", trace[:4000] or "Fatal error")

        elif mtype == "quit_ack":
            pass


    def start_recording(self):
        self._ensure_worker()

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.out_dir = os.path.join(os.getcwd(), f"psr_like_{ts}")

        self._restart_worker_with_current_config()

        self._send({"type": "start", "out_dir": self.out_dir})

    def stop_recording(self):
        self._send({"type": "stop"})

    def add_note(self):
        txt = self.note_text.get("1.0", "end").strip()
        if not txt:
            txt = "(Notiz ohne Text)"
        self._send({"type": "note", "text": txt})
        self.note_text.delete("1.0", "end")

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