# Chisel — The interactive PDF editor

A native, open-source PDF editor for Linux. Annotate documents, edit text, manage pages, redact content, and more — all with a polished GTK4/Adwaita interface. No cloud, no subscriptions, no tracking.

---

## Features

📝 **Edit text in place** — Click any text span and rewrite it directly on the page. Undo and redo supported.

🖍️ **Annotate & markup** — Highlights, lines, arrows, rectangles, circles, and callout boxes with customizable stroke color, width, and fill.

✂️ **Redact** — Permanently remove sensitive content with the cut tool. Draw a rectangle and apply — the content is gone.

🖼️ **Insert images** — Place images onto pages by clicking or dragging a rectangle. Paste from clipboard too.

🧮 **Fraction editor** — Detects mathematical fractions in PDF text and opens a dedicated editing dialog.

📄 **Page management** — Insert, delete, duplicate, and reorder pages. Continuous scroll or single-page view.

↩️ **Undo / redo** — Full journal-based undo history. Undo anything, even across pages.

🌗 **Dark mode** — Follows your system theme via Adwaita. No config needed.

🔍 **Thumbnail sidebar** — Zoomable page thumbnails with right-click context menu for page operations.

---

## Install

### System dependencies

Ubuntu / Debian:
```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gdkpixbuf-2.0
```

Fedora:
```bash
sudo dnf install python3-gobject gtk4 libadwaita
```

### Install Chisel

```bash
pip install git+https://github.com/atomHoliday/Chisel.git
```

### Run

```bash
chisel

# or directly from a checkout
git clone https://github.com/atomHoliday/Chisel.git
cd chisel
python main.py
```

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| Ctrl+O | Open PDF |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| Ctrl+C | Copy selected |
| Ctrl+V | Paste |
| Delete | Delete selected |
| Escape | Cancel / clear selection |
| + / - | Zoom in / out |
| Ctrl+scroll | Zoom |
| Ctrl+drag | Pan |
| Page Up / Down | Navigate pages |
| Home / End | First / last page |
