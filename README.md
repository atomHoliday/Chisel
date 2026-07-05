# Chisel

The interactive PDF editor.

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
pip install git+https://github.com/youruser/chisel.git
```

### Run

```bash
chisel

# or directly from a checkout
git clone https://github.com/youruser/chisel.git
cd chisel
python main.py
```

## Features

- Open and save PDF files
- Annotate — highlights, lines, arrows, shapes, callouts
- Edit text in place
- Fraction detection and editing
- Insert and paste images
- Cut / redact content
- Undo / redo (Ctrl+Z / Ctrl+Shift+Z)
- Continuous scroll or single-page view
- Dark mode support
- Zoomable page thumbnail sidebar

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
