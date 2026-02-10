# PSRLike

PSRLike records user actions and generates an end-user style guide with screenshots (clicks highlighted) and optional per-monitor video — similar to Windows “Problem Steps Recorder”.

## Features
- Click tracking + screenshots with click marker  
- Text input detection (e.g., typed URLs) included in the instructions  
- Multi-monitor support (steps mapped to the correct screen)  
- Configurable screenshot delay (useful for menus)  
- Export: **HTML**, **DOCX**, **PDF**  
- GUI Start/Stop clicks are excluded from recording

## Run (dev)
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt
python gui/app.py
```

## Build Windows EXE (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name PSRLike gui/app.py
```
Output: ``dist/PSRLike.exe``

Notes:
- Text input is captured when you press Enter or Tab (and then shown in the guide).
- On macOS you must allow Screen Recording and Input Monitoring in Privacy & Security.


