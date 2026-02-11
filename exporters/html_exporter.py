from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict


def export_html(out_dir: str, title: str = "Anleitung"):
    steps_path = os.path.join(out_dir, "steps.json")
    if not os.path.exists(steps_path):
        raise FileNotFoundError(f"steps.json not found in {out_dir}")

    with open(steps_path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    created = datetime.now().strftime("%d.%m.%Y %H:%M")
    html_path = os.path.join(out_dir, "anleitung.html")

    html = f"""<!doctype html>
<html lang="de" data-theme="auto">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{_esc(title)}</title>
<style>
:root {{
  --radius: 14px;
  --radius2: 12px;
  --font: system-ui, -apple-system, Segoe UI, Roboto, Arial;

  --shadow: 0 12px 30px rgba(0,0,0,.12);
  --shadow2: 0 8px 18px rgba(0,0,0,.10);
}}

html[data-theme="dark"] {{
  --bg: #0b0d12;
  --bg2: #0f131a;
  --card: #141a23;
  --card2: #101621;
  --line: rgba(255,255,255,.14);
  --text: #eef0f6;
  --muted: rgba(238,240,246,.70);

  --accent: #4f8cff;
  --danger: #ff4f6d;
  --ok: #3ddc97;

  --btn: #1a2230;
  --btnHover: #202a3b;
  --input: #0f1520;

  --toastBg: #121621;
  --toastLine: rgba(255,255,255,.14);
}}

html[data-theme="light"] {{
  --bg: #f6f7fb;
  --bg2: #ffffff;
  --card: #ffffff;
  --card2: #fbfbfd;
  --line: rgba(0,0,0,.12);
  --text: #0a1022;
  --muted: rgba(10,16,34,.66);

  --accent: #2f6fff;
  --danger: #d91e3f;
  --ok: #10a76b;

  --btn: #f1f3f8;
  --btnHover: #e8ecf6;
  --input: #ffffff;

  --toastBg: #111318;
  --toastLine: rgba(255,255,255,.14);
}}

* {{ box-sizing: border-box; }}
html, body {{ height: 100%; }}

body {{
  margin: 0;
  font-family: var(--font);
  color: var(--text);
  background: var(--bg);
}}

.wrap {{
  max-width: 1120px;
  margin: 0 auto;
  padding: 22px 16px 56px;
}}

header {{
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--card);
  padding: 14px;
  box-shadow: var(--shadow);
}}

.hrow {{
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}}

.titlebox {{
  min-width: min(640px, 100%);
}}

h1 {{
  margin: 0;
  font-size: 1.45rem;
  letter-spacing: .2px;
  line-height: 1.2;
  outline: none;
}}

.meta {{
  margin-top: 8px;
  color: var(--muted);
  font-size: .95rem;
}}

.actions {{
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
}}

button {{
  appearance: none;
  border: 1px solid var(--line);
  background: var(--btn);
  color: var(--text);
  padding: 9px 12px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 650;
  letter-spacing: .1px;
  transition: background .12s ease, border-color .12s ease, transform .08s ease;
}}

button:hover {{
  background: var(--btnHover);
  border-color: rgba(79,140,255,.55);
}}

button:active {{
  transform: translateY(1px);
}}

button.primary {{
  border-color: rgba(79,140,255,.70);
}}

button.danger {{
  border-color: rgba(255,79,109,.55);
}}

button.ghost {{
  background: transparent;
}}

main {{
  margin-top: 14px;
  display: grid;
  gap: 12px;
}}

.card {{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 12px;
  box-shadow: var(--shadow2);
}}

.stephead {{
  display: grid;
  grid-template-columns: 44px 1fr auto;
  gap: 12px;
  align-items: start;
}}

.badge {{
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-weight: 850;
  background: var(--btn);
  border: 1px solid rgba(79,140,255,.55);
  color: var(--text);
}}

.small {{
  color: var(--muted);
  font-size: .92rem;
  margin-top: 8px;
}}

.input {{
  width: 100%;
  border: 1px solid var(--line);
  background: var(--input);
  color: var(--text);
  border-radius: var(--radius2);
  padding: 11px 12px;
  outline: none;
  font-size: 1.02rem;
  line-height: 1.28rem;
  resize: vertical;
  min-height: 52px;
}}

.input:focus {{
  border-color: rgba(79,140,255,.80);
  box-shadow: 0 0 0 3px rgba(79,140,255,.18);
}}

.rowbtns {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}}

.imgwrap {{
  margin-top: 12px;
  border-radius: var(--radius2);
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--card2);
}}

.imgwrap img {{
  width: 100%;
  display: block;
}}

.imgtools {{
  margin-top: 10px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}}

.file {{ display: none; }}

label.filebtn {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--line);
  background: var(--btn);
  color: var(--text);
  padding: 9px 12px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 650;
  transition: background .12s ease, border-color .12s ease, transform .08s ease;
}}

label.filebtn:hover {{
  background: var(--btnHover);
  border-color: rgba(79,140,255,.55);
}}

label.filebtn:active {{
  transform: translateY(1px);
}}

.toast {{
  position: fixed;
  left: 16px;
  bottom: 16px;
  background: var(--toastBg);
  border: 1px solid var(--toastLine);
  color: #fff;
  padding: 10px 12px;
  border-radius: 12px;
  opacity: 0;
  transform: translateY(8px);
  transition: opacity .18s ease, transform .18s ease;
  pointer-events: none;
  max-width: min(560px, calc(100vw - 32px));
  white-space: pre-wrap;
  box-shadow: var(--shadow2);
}}

.toast.show {{
  opacity: 1;
  transform: translateY(0);
}}

.dropdown {{
  position: relative;
}}

.menu {{
  position: absolute;
  right: 0;
  top: calc(100% + 10px);
  min-width: 260px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--card);
  box-shadow: var(--shadow);
  padding: 8px;
  display: none;
}}

.menu.show {{
  display: block;
}}

.menu button {{
  width: 100%;
  text-align: left;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 10px;
  border-radius: 10px;
  background: transparent;
  border: 1px solid transparent;
  font-weight: 650;
}}

.menu button:hover {{
  background: var(--btnHover);
  border-color: var(--line);
}}

.kbd {{
  font-size: .85rem;
  color: var(--muted);
}}

@media (max-width: 860px) {{
  .titlebox {{ min-width: 100%; }}
}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="hrow">
      <div class="titlebox">
        <h1 contenteditable="true" id="docTitle">{_esc(title)}</h1>
        <div class="meta">Erstellt: {created}</div>
      </div>
      <div class="actions">
        <button class="ghost" id="btnTheme" title="Theme wechseln">Theme</button>
        <button class="primary" id="btnSaveLocal">Im Browser speichern</button>

        <div class="dropdown">
          <button class="ok" id="btnDownload">Herunterladen</button>
          <div class="menu" id="downloadMenu" role="menu" aria-hidden="true">
            <button id="mDocx" role="menuitem">Als DOCX speichern <span class="kbd">DOCX</span></button>
            <button id="mHtml" role="menuitem">Als HTML speichern <span class="kbd">HTML</span></button>
            <button id="mJson" role="menuitem">JSON herunterladen <span class="kbd">JSON</span></button>
          </div>
        </div>

        <button class="danger" id="btnReset">Zurücksetzen</button>
      </div>
    </div>
  </header>

  <main id="steps"></main>
  <div class="toast" id="toast"></div>
</div>

<script id="initialData" type="application/json">{json.dumps(data, ensure_ascii=False)}</script>
<script src="https://cdn.jsdelivr.net/npm/docx@8.5.0/build/index.umd.js"></script>
<script src="https://cdn.jsdelivr.net/npm/file-saver@2.0.5/dist/FileSaver.min.js"></script>
<script>
const ORIGINAL = JSON.parse(document.getElementById("initialData").textContent || "{{}}");
const STORAGE_KEY = "psrlike_editor_state_" + location.pathname;

function deepCopy(x) {{ return JSON.parse(JSON.stringify(x)); }}

function preferTheme() {{
  try {{
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }} catch (e) {{
    return "dark";
  }}
}}

function applyTheme(theme) {{
  const root = document.documentElement;
  if (theme === "auto") theme = preferTheme();
  root.setAttribute("data-theme", theme);
}}

function loadTheme() {{
  try {{
    const t = localStorage.getItem("psrlike_theme");
    if (!t) return "auto";
    return t;
  }} catch (e) {{
    return "auto";
  }}
}}

function saveTheme(t) {{
  try {{ localStorage.setItem("psrlike_theme", t); }} catch(e) {{}}
}}

let THEME = loadTheme();
applyTheme(THEME);

try {{
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  mq.addEventListener("change", () => {{
    if ((loadTheme() || "auto") === "auto") applyTheme("auto");
  }});
}} catch(e) {{}}

function loadState() {{
  try {{
    const s = localStorage.getItem(STORAGE_KEY);
    if (!s) return deepCopy(ORIGINAL);
    const parsed = JSON.parse(s);
    if (!parsed || typeof parsed !== "object") return deepCopy(ORIGINAL);
    return parsed;
  }} catch(e) {{
    return deepCopy(ORIGINAL);
  }}
}}

function saveState(state) {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}}

function toast(msg) {{
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove("show"), 1500);
}}

function normalizeEvents(state) {{
  const ev = (state.events || []).filter(e => ["mouse_click","key_press","text_input"].includes((e.kind||"")));
  state.events = ev;
  return state;
}}

let STATE = normalizeEvents(loadState());

function getStepText(e) {{
  return (e.instruction || e.detail || "").trim();
}}

async function fileToDataUrl(file) {{
  return new Promise((resolve, reject) => {{
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  }});
}}

function download(filename, text, mime) {{
  const blob = new Blob([text], {{type: mime}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}}

function buildHtmlFromCurrent() {{
  const title = (document.getElementById("docTitle").textContent || "Anleitung").trim();
  const doc = document.documentElement.cloneNode(true);
  const scriptData = doc.querySelector("#initialData");
  if (scriptData) scriptData.textContent = JSON.stringify(STATE);
  const t = doc.querySelector("title");
  if (t) t.textContent = title;
  const h1 = doc.querySelector("#docTitle");
  if (h1) h1.textContent = title;
  return "<!doctype html>\\n" + doc.outerHTML;
}}

function render() {{
  const root = document.getElementById("steps");
  root.innerHTML = "";
  const events = STATE.events || [];
  const monitors = new Map((STATE.monitors || []).map(m => [m.index, m]));

  events.forEach((e, idx) => {{
    const card = document.createElement("section");
    card.className = "card";
    const badgeNo = idx + 1;

    const mon = e.monitor_index != null ? monitors.get(e.monitor_index) : null;
    const ctxParts = [];
    if (e.app_name) ctxParts.push(e.app_name);
    if (e.window_title) ctxParts.push(e.window_title);
    if (mon && mon.width && mon.height) ctxParts.push("Monitor " + mon.index + " (" + mon.width + "×" + mon.height + ")");
    const ctx = ctxParts.join(" · ");

    const head = document.createElement("div");
    head.className = "stephead";

    const badge = document.createElement("div");
    badge.className = "badge";
    badge.textContent = badgeNo;

    const mid = document.createElement("div");
    const input = document.createElement("textarea");
    input.className = "input";
    input.rows = 2;
    input.value = getStepText(e);
    input.addEventListener("input", () => {{
      e.instruction = input.value;
      saveState(STATE);
    }});

    const meta = document.createElement("div");
    meta.className = "small";
    meta.textContent = ctx ? ctx : "";

    mid.appendChild(input);
    if (ctx) mid.appendChild(meta);

    const btns = document.createElement("div");
    btns.className = "rowbtns";

    const up = document.createElement("button");
    up.textContent = "↑";
    up.title = "Schritt nach oben";
    up.disabled = idx === 0;
    up.addEventListener("click", () => {{
      if (idx <= 0) return;
      const arr = STATE.events;
      const tmp = arr[idx-1];
      arr[idx-1] = arr[idx];
      arr[idx] = tmp;
      saveState(STATE);
      render();
    }});

    const down = document.createElement("button");
    down.textContent = "↓";
    down.title = "Schritt nach unten";
    down.disabled = idx === events.length - 1;
    down.addEventListener("click", () => {{
      if (idx >= events.length - 1) return;
      const arr = STATE.events;
      const tmp = arr[idx+1];
      arr[idx+1] = arr[idx];
      arr[idx] = tmp;
      saveState(STATE);
      render();
    }});

    const del = document.createElement("button");
    del.className = "danger";
    del.textContent = "Löschen";
    del.addEventListener("click", () => {{
      STATE.events.splice(idx, 1);
      saveState(STATE);
      render();
    }});

    btns.appendChild(up);
    btns.appendChild(down);
    btns.appendChild(del);

    head.appendChild(badge);
    head.appendChild(mid);
    head.appendChild(btns);

    card.appendChild(head);

    const shot = e.screenshot;
    if (shot) {{
      const imgwrap = document.createElement("div");
      imgwrap.className = "imgwrap";
      const img = document.createElement("img");
      img.src = shot;
      img.alt = "Schritt " + badgeNo;
      imgwrap.appendChild(img);
      card.appendChild(imgwrap);
    }}

    const tools = document.createElement("div");
    tools.className = "imgtools";

    const rm = document.createElement("button");
    rm.textContent = shot ? "Bild entfernen" : "Kein Bild";
    rm.className = shot ? "danger" : "";
    rm.disabled = !shot;
    rm.addEventListener("click", () => {{
      e.screenshot = null;
      saveState(STATE);
      render();
    }});

    const fileId = "file_" + idx + "_" + Math.random().toString(16).slice(2);
    const file = document.createElement("input");
    file.type = "file";
    file.accept = "image/*";
    file.className = "file";
    file.id = fileId;

    file.addEventListener("change", async () => {{
      const f = file.files && file.files[0];
      if (!f) return;
      const url = await fileToDataUrl(f);
      e.screenshot = url;
      saveState(STATE);
      render();
      toast("Bild hinzugefügt");
    }});

    const lbl = document.createElement("label");
    lbl.className = "filebtn";
    lbl.setAttribute("for", fileId);
    lbl.textContent = shot ? "Bild ersetzen" : "Bild hinzufügen";

    tools.appendChild(rm);
    tools.appendChild(lbl);
    tools.appendChild(file);

    card.appendChild(tools);

    root.appendChild(card);
  }});
}}

async function imgSrcToBytes(src) {{
  try {{
    if (!src) return null;
    if (src.startsWith("data:")) {{
      const res = await fetch(src);
      const ab = await res.arrayBuffer();
      return new Uint8Array(ab);
    }}
    const img = new Image();
    img.decoding = "async";
    img.src = src;
    await new Promise((resolve, reject) => {{
      img.onload = resolve;
      img.onerror = reject;
    }});
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);
    const dataUrl = canvas.toDataURL("image/png");
    const res = await fetch(dataUrl);
    const ab = await res.arrayBuffer();
    return new Uint8Array(ab);
  }} catch(e) {{
    return null;
  }}
}}

function scaleToFit(w, h, maxW, maxH) {{
  const s = Math.min(maxW / w, maxH / h, 1);
  return [Math.round(w*s), Math.round(h*s)];
}}

async function exportDocx() {{
  if (!window.docx || !window.saveAs) {{
    toast("DOCX-Export benötigt Internet (docx.js/file-saver).");
    return;
  }}
  const title = (document.getElementById("docTitle").textContent || "Anleitung").trim();
  const events = STATE.events || [];
  const docxApi = window.docx;

  const children = [];
  children.push(new docxApi.Paragraph({{ text: title, heading: docxApi.HeadingLevel.TITLE }}));
  children.push(new docxApi.Paragraph({{ text: " ", spacing: {{ after: 140 }} }}));

  for (let i = 0; i < events.length; i++) {{
    const e = events[i];
    const text = getStepText(e);
    if (!text) continue;

    children.push(new docxApi.Paragraph({{
      children: [new docxApi.TextRun({{ text: (i + 1) + ". " + text, bold: true }})],
      spacing: {{ after: 120 }}
    }}));

    const ctxParts = [];
    if (e.app_name) ctxParts.push(e.app_name);
    if (e.window_title) ctxParts.push(e.window_title);
    const ctx = ctxParts.join(" · ");
    if (ctx) {{
      children.push(new docxApi.Paragraph({{ text: ctx, spacing: {{ after: 120 }} }}));
    }}

    if (e.screenshot) {{
      const bytes = await imgSrcToBytes(e.screenshot);
      if (bytes) {{
        const img = new Image();
        img.src = e.screenshot;
        await new Promise((resolve) => {{ img.onload = resolve; img.onerror = resolve; }});
        const [tw, th] = scaleToFit(img.naturalWidth || 1200, img.naturalHeight || 800, 620, 380);
        children.push(new docxApi.Paragraph({{
          children: [new docxApi.ImageRun({{
            data: bytes,
            transformation: {{ width: tw, height: th }}
          }})],
          spacing: {{ after: 240 }}
        }}));
      }}
    }}

    children.push(new docxApi.Paragraph({{ text: " ", spacing: {{ after: 80 }} }}));
  }}

  const doc = new docxApi.Document({{ sections: [{{ properties: {{}}, children: children }}] }});
  const blob = await docxApi.Packer.toBlob(doc);
  window.saveAs(blob, (title || "Anleitung") + ".docx");
}}

function closeMenu() {{
  const m = document.getElementById("downloadMenu");
  m.classList.remove("show");
  m.setAttribute("aria-hidden", "true");
}}

function toggleMenu() {{
  const m = document.getElementById("downloadMenu");
  const open = m.classList.contains("show");
  if (open) {{
    closeMenu();
  }} else {{
    m.classList.add("show");
    m.setAttribute("aria-hidden", "false");
  }}
}}

document.getElementById("btnTheme").addEventListener("click", () => {{
  const current = loadTheme() || "auto";
  const next = current === "auto" ? "dark" : (current === "dark" ? "light" : "auto");
  saveTheme(next);
  THEME = next;
  applyTheme(next);
  toast(next === "auto" ? "Theme: automatisch" : ("Theme: " + (next === "dark" ? "dunkel" : "hell")));
}});

document.getElementById("btnSaveLocal").addEventListener("click", () => {{
  saveState(STATE);
  toast("Gespeichert");
}});

document.getElementById("btnDownload").addEventListener("click", (e) => {{
  e.stopPropagation();
  toggleMenu();
}});

document.getElementById("mJson").addEventListener("click", () => {{
  closeMenu();
  const payload = deepCopy(STATE);
  const t = (document.getElementById("docTitle").textContent || "Anleitung").trim();
  payload.title = t;
  download("steps.edited.json", JSON.stringify(payload, null, 2), "application/json");
}});

document.getElementById("mHtml").addEventListener("click", () => {{
  closeMenu();
  const html = buildHtmlFromCurrent();
  download("anleitung.edited.html", html, "text/html");
}});

document.getElementById("mDocx").addEventListener("click", () => {{
  closeMenu();
  exportDocx();
}});

document.getElementById("btnReset").addEventListener("click", () => {{
  STATE = normalizeEvents(deepCopy(ORIGINAL));
  saveState(STATE);
  toast("Zurückgesetzt");
  render();
}});

document.addEventListener("click", () => closeMenu());
document.addEventListener("keydown", (e) => {{
  if (e.key === "Escape") closeMenu();
}});

render();
</script>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return html_path


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")