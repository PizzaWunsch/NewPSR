from __future__ import annotations

import os
import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Dict


def get_active_window_info() -> Optional[Dict[str, str]]:
    if sys.platform != "win32":
        return None

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = (buf.value or "").strip()

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    pid_val = int(pid.value) if pid.value else 0

    app_path = ""
    app_name = ""

    if pid_val:
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        hproc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid_val)
        if hproc:
            try:
                size = wintypes.DWORD(32768)
                path_buf = ctypes.create_unicode_buffer(size.value)
                QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
                QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
                ok = QueryFullProcessImageNameW(hproc, 0, path_buf, ctypes.byref(size))
                if ok:
                    app_path = path_buf.value
                    app_name = os.path.basename(app_path) if app_path else ""
            finally:
                kernel32.CloseHandle(hproc)

    out = {}
    if title:
        out["window_title"] = title
    if app_name:
        out["app_name"] = app_name
    if app_path:
        out["app_path"] = app_path
    return out or None