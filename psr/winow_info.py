import win32gui
import win32process
import psutil


def get_window_info_at_point(x: int, y: int) -> dict | None:
    try:
        hwnd = win32gui.WindowFromPoint((x, y))
        if not hwnd:
            return None

        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid).name() if pid else None

        rect = win32gui.GetWindowRect(hwnd)

        return {
            "hwnd": int(hwnd),
            "title": title,
            "class": class_name,
            "process": process,
            "rect": {
                "left": rect[0],
                "top": rect[1],
                "right": rect[2],
                "bottom": rect[3],
            },
        }
    except Exception:
        return None
