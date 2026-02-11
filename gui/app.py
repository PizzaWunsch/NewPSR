from __future__ import annotations

import os
import sys
import time
import webbrowser
import multiprocessing as mp
from dataclasses import dataclass
from typing import Any, Dict, Optional

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from gui.recorder_process import recorder_worker
from psr.recordings_store import list_recordings, rename_recording, delete_recording, create_recording_dir
from psr.paths import recordings_root_dir


@dataclass
class AppConfig:
    enable_video: bool = False
    video_fps: int = 8
    screenshot_delay_ms: int = 0
    record_text_input: bool = True


class RecorderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PSR Recorder")
        self.root.geometry("1020x640")

        self.cfg = AppConfig()
        self._proc: Optional[mp.Process] = None
        self._parent_conn = None
        self._child_conn = None

        self._recording_out_dir: Optional[str] = None
        self._last_html_path: Optional[str] = None

        self._build_ui()
        self.refresh_recordings()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(150, self._poll_worker)

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        top = ttk.Frame(outer)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Bereit.")
        ttk.Label(top, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

        btns = ttk.Frame(top)
        btns.grid(row=0, column=1, sticky="e")

        self.btn_start = ttk.Button(btns, text="Start", command=self.start_recording)
        self.btn_stop = ttk.Button(btns, text="Stop", command=self.stop_recording, state="disabled")
        self.btn_open = ttk.Button(btns, text="Öffnen", command=self.open_selected)
        self.btn_open_folder = ttk.Button(btns, text="Ordner öffnen", command=self.open_selected_folder)
        self.btn_rename = ttk.Button(btns, text="Umbenennen", command=self.rename_selected)
        self.btn_delete = ttk.Button(btns, text="Löschen", command=self.delete_selected)

        self.btn_start.grid(row=0, column=0, padx=(0, 6))
        self.btn_stop.grid(row=0, column=1, padx=(0, 12))
        self.btn_open.grid(row=0, column=2, padx=(0, 6))
        self.btn_open_folder.grid(row=0, column=3, padx=(0, 12))
        self.btn_rename.grid(row=0, column=4, padx=(0, 6))
        self.btn_delete.grid(row=0, column=5)

        cfg = ttk.LabelFrame(outer, text="Aufnahme-Einstellungen", padding=10)
        cfg.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        cfg.columnconfigure(6, weight=1)

        self.var_record_text = tk.BooleanVar(value=self.cfg.record_text_input)
        self.var_enable_video = tk.BooleanVar(value=self.cfg.enable_video)
        self.var_video_fps = tk.IntVar(value=self.cfg.video_fps)
        self.var_delay_ms = tk.IntVar(value=self.cfg.screenshot_delay_ms)

        ttk.Checkbutton(cfg, text="Text-Eingaben aufnehmen", variable=self.var_record_text).grid(
            row=0, column=0, sticky="w", padx=(0, 14)
        )
        ttk.Checkbutton(cfg, text="Video aktivieren", variable=self.var_enable_video).grid(
            row=0, column=1, sticky="w", padx=(0, 14)
        )

        ttk.Label(cfg, text="FPS").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(cfg, from_=1, to=60, textvariable=self.var_video_fps, width=6).grid(
            row=0, column=3, sticky="w", padx=(6, 14)
        )

        ttk.Label(cfg, text="Screenshot-Delay (ms)").grid(row=0, column=4, sticky="w")
        ttk.Spinbox(cfg, from_=0, to=5000, increment=50, textvariable=self.var_delay_ms, width=8).grid(
            row=0, column=5, sticky="w", padx=(6, 14)
        )

        self.btn_apply_cfg = ttk.Button(cfg, text="Übernehmen", command=self.apply_config)
        self.btn_apply_cfg.grid(row=0, column=6, sticky="e")

        main = ttk.Frame(outer)
        main.grid(row=2, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        ttk.Label(main, text="Recordings (Historie)").grid(row=0, column=0, sticky="w", pady=(0, 6))

        cols = ("name", "created", "has_steps", "has_html")
        self.tree = ttk.Treeview(main, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Name")
        self.tree.heading("created", text="Geändert")
        self.tree.heading("has_steps", text="Steps")
        self.tree.heading("has_html", text="HTML")

        self.tree.column("name", width=560, anchor="w")
        self.tree.column("created", width=180, anchor="w")
        self.tree.column("has_steps", width=60, anchor="center")
        self.tree.column("has_html", width=60, anchor="center")

        ysb = ttk.Scrollbar(main, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        ysb.grid(row=1, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda e: self.open_selected())


    def apply_config(self):
        try:
            fps = int(self.var_video_fps.get())
            if fps < 1:
                fps = 1

            delay = int(self.var_delay_ms.get())
            if delay < 0:
                delay = 0

            self.cfg = AppConfig(
                enable_video=bool(self.var_enable_video.get()),
                video_fps=fps,
                screenshot_delay_ms=delay,
                record_text_input=bool(self.var_record_text.get()),
            )

            if self._proc and self._proc.is_alive():
                self._restart_worker()

            self.status_var.set("Einstellungen übernommen.")
        except Exception as e:
            messagebox.showerror("Fehler", str(e), parent=self.root)

    def _restart_worker(self):
        try:
            if self._parent_conn:
                try:
                    self._parent_conn.send({"type": "quit"})
                except Exception:
                    pass
        finally:
            try:
                if self._proc and self._proc.is_alive():
                    self._proc.terminate()
            except Exception:
                pass

        try:
            if self._parent_conn:
                try:
                    self._parent_conn.close()
                except Exception:
                    pass
            if self._child_conn:
                try:
                    self._child_conn.close()
                except Exception:
                    pass
        except Exception:
            pass

        self._proc = None
        self._parent_conn = None
        self._child_conn = None

        self._ensure_worker()

    def refresh_recordings(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        items = list_recordings()
        for it in items:
            created = time.strftime("%Y-%m-%d %H:%M", time.localtime(it.created_ts))
            self.tree.insert(
                "",
                "end",
                values=(it.name, created, "✓" if it.has_steps else "", "✓" if it.has_html else ""),
                tags=(it.path,),
            )

        if items:
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)

    def _selected_path(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        tags = self.tree.item(iid, "tags")
        if tags:
            return tags[0]
        return None

    def _ensure_worker(self):
        if self._proc and self._proc.is_alive():
            return

        if self._parent_conn:
            try:
                self._parent_conn.close()
            except Exception:
                pass
        if self._child_conn:
            try:
                self._child_conn.close()
            except Exception:
                pass

        self._parent_conn, self._child_conn = mp.Pipe()

        cfg_dict: Dict[str, Any] = {
            "screenshot_on_keys": (),
            "enable_video": self.cfg.enable_video,
            "video_fps": self.cfg.video_fps,
            "screenshot_delay_ms": self.cfg.screenshot_delay_ms,
            "record_text_input": self.cfg.record_text_input,
        }

        self._proc = mp.Process(target=recorder_worker, args=(self._child_conn, cfg_dict), daemon=True)
        self._proc.start()

    def start_recording(self):
        try:
            self._ensure_worker()

            out_dir = create_recording_dir()
            self._recording_out_dir = out_dir

            self._parent_conn.send({"type": "start", "out_dir": out_dir})
            self.status_var.set("Starte Recording …")
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Fehler", str(e), parent=self.root)
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")

    def stop_recording(self):
        try:
            if not self._parent_conn:
                return
            self._parent_conn.send({"type": "stop"})
            self.status_var.set("Stoppe Recording …")
            self.btn_stop.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("Fehler", str(e), parent=self.root)
            self.btn_stop.configure(state="normal")

    def open_selected(self):
        path = self._selected_path()
        if not path:
            return

        html = os.path.join(path, "anleitung.html")
        steps = os.path.join(path, "steps.json")

        if os.path.exists(html):
            self._last_html_path = html
            webbrowser.open("file://" + os.path.abspath(html))
            self.status_var.set("Öffne HTML …")
            return

        if os.path.exists(steps):
            self._open_folder(path)
            self.status_var.set("HTML fehlt – Ordner geöffnet.")
            return

        messagebox.showwarning(
            "Hinweis",
            "In diesem Recording sind keine Dateien (steps.json/anleitung.html) gefunden.",
            parent=self.root,
        )

    def open_selected_folder(self):
        path = self._selected_path()
        if not path:
            path = recordings_root_dir()
        self._open_folder(path)
        self.status_var.set("Ordner geöffnet.")

    def rename_selected(self):
        path = self._selected_path()
        if not path:
            return

        current_name = os.path.basename(path.rstrip("/\\"))
        new_name = simpledialog.askstring("Umbenennen", "Neuer Name:", initialvalue=current_name, parent=self.root)
        if not new_name:
            return

        try:
            new_path = rename_recording(path, new_name)
            self.status_var.set("Umbenannt.")
            self.refresh_recordings()
            self._select_by_path(new_path)
        except Exception as e:
            messagebox.showerror("Fehler", str(e), parent=self.root)

    def delete_selected(self):
        path = self._selected_path()
        if not path:
            return

        name = os.path.basename(path.rstrip("/\\"))
        if not messagebox.askyesno("Löschen", f"Recording wirklich löschen?\n\n{name}", parent=self.root):
            return

        try:
            delete_recording(path)
            self.status_var.set("Gelöscht.")
            self.refresh_recordings()
        except Exception as e:
            messagebox.showerror("Fehler", str(e), parent=self.root)

    def _select_by_path(self, path: str):
        for iid in self.tree.get_children():
            tags = self.tree.item(iid, "tags")
            if tags and os.path.abspath(tags[0]) == os.path.abspath(path):
                self.tree.selection_set(iid)
                self.tree.see(iid)
                return

    def _open_folder(self, path: str):
        try:
            if sys.platform.startswith("darwin"):
                os.system(f'open "{path}"')
            elif os.name == "nt":
                os.system(f'explorer "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception:
            pass

    # ---------------- Worker polling ----------------

    def _poll_worker(self):
        try:
            if self._parent_conn and self._parent_conn.poll():
                msg = self._parent_conn.recv()
                self._handle_worker_msg(msg)
        except Exception:
            pass
        finally:
            self.root.after(120, self._poll_worker)

    def _handle_worker_msg(self, msg: Dict[str, Any]):
        t = msg.get("type")

        if t == "ready":
            self.status_var.set("Bereit.")
            return

        if t == "started":
            self.status_var.set("Recording läuft … (Stop zum Beenden)")
            return

        if t == "stopped":
            out_dir = msg.get("out_dir")
            out_path = msg.get("out_path")
            export_error = msg.get("export_error")

            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")

            if export_error:
                self.status_var.set(f"Recording gestoppt, Export-Fehler: {export_error}")
            else:
                self.status_var.set("Recording gestoppt. HTML erstellt.")
                if out_path and os.path.exists(out_path):
                    self._last_html_path = out_path
                    webbrowser.open("file://" + os.path.abspath(out_path))

            self.refresh_recordings()
            if out_dir:
                self._select_by_path(out_dir)
            return

        if t == "error":
            self.status_var.set("Fehler: " + str(msg.get("message") or ""))
            return

        if t == "fatal":
            trace = msg.get("trace") or ""
            messagebox.showerror("Fatal", trace[:4000] if trace else "Fataler Fehler im Worker.", parent=self.root)
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            return


    def on_close(self):
        try:
            if self._parent_conn:
                try:
                    self._parent_conn.send({"type": "quit"})
                except Exception:
                    pass
        finally:
            try:
                if self._proc and self._proc.is_alive():
                    self._proc.terminate()
            except Exception:
                pass
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    RecorderGUI().run()