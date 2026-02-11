from __future__ import annotations

import os
import sys


def app_root_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.getcwd())


def recordings_root_dir() -> str:
    p = os.path.join(app_root_dir(), "recordings")
    os.makedirs(p, exist_ok=True)
    return p