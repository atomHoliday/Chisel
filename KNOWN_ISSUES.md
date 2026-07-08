# Known Issues

## Active — Major

| # | Issue | File | Description |
|---|-------|------|-------------|
| M1 | **Sidebar thumbnail click resets to first page on first click** | `window.py:417-422` | Clicking a page thumbnail in the sidebar on the first attempt resets to page 0 instead of the target page. Second click works correctly. Likely a signal-ordering issue between `row-selected` and `row-activated` after `rebuild()`. |
| M2 | **Text editing removes overlapping annotations** | `text_edit_tool.py:143-147` | `apply_redactions()` in `_apply_edit` destroys any annotation that overlaps the text span's bounding box. Fraction editor already captures overlapping drawings before redacting and re-draws them; text editor needs the same treatment. |

## Active — Minor

| # | Issue | File | Description |
|---|-------|------|-------------|
| N1 | **`Gdk.cairo_set_source_pixbuf` deprecated** | `canvas.py:355, 409` | Works in GTK 4.22 (PyGObject provides it) but logs a deprecation warning. Replacement API `Gdk.cairo_set_source_texture` not available in this GTK version. |
| N2 | **Text width heuristic for paste preview** | `select_tool.py:510` | `len(text) * fs * 0.65 + 16` is a rough estimate that doesn't account for font metrics or individual glyph widths. |
| N3 | **`get_allocation()` returns zeros before widget is realized** | `image_tool.py:149`, `window.py:855` | Both callers guard against `width <= 0` / `height <= 0`, so no crash, but means paste-centering fails before first draw. |

## Fixed

| # | Issue | File | Fix |
|---|-------|------|-----|
| F1 | **CSS path wrong** | `window.py:660` | `_load_css` now uses correct path one level up. |
| F2 | **DEBUG=True in production** | `debug/__init__.py:16` | Set to `False`. |
| F3 | **Log file writes to package dir** | `debug/__init__.py:23` | Removed `FileHandler`; stream-only logging. |
| F4 | **Private build backend** | `pyproject.toml:3` | Changed to `setuptools.build_meta`. |
| F5 | **Missing SVG icon in meson.build** | `meson.build:50` | Removed reference to non-existent file. |
| F6 | **Pervasive private-attribute access** | cross-module | Added `PdfDocument.doc` property, `PdfCanvas.invalidate_cache()`/`invalidate_page_cache()`/`selected_item` property, `PageManager.document` property. All external consumers updated. |
| F7 | **Canvas scroll reset on resize** | `canvas.py:328-331` | Removed scroll reset block; pan position preserved across resizes. |
| F8 | **Unbounded page cache** | `canvas.py:71` | Replaced plain dict with `OrderedDict`, capped at `MAX_CACHE_SIZE=32` with LRU eviction. |
| F9 | **Font preload mutates document** | `pdf_document.py:28-39` | Removed `_preload_fonts()` entirely; PyMuPDF loads fonts lazily. |
| F10 | **`page_to_canvas` unused, `canvas_to_page` parameter naming** | `tools/base.py:44-48` | Removed dead `page_to_canvas`; renamed `scroll_x/y` → `draw_x/y` in `canvas_to_page`. |
| F11 | **`page.annots()` called twice** | `select_tool.py:241` | Changed to `list(page.annots() or [])`. |
| F12 | **Incremental save with journal enabled** | `pdf_document.py:67-68` | Removed `incremental=True`; always do full save with journal. |
| F13 | **Startup crash: `set_width_request` doesn't exist in GTK4** | `window.py:325` | Changed to `set_size_request(180, -1)`. |
| F14 | **`margin-end` CSS property doesn't exist in GTK4** | `style.css:74` | Changed to `margin-right`. |
| F15 | **Page scale breaks on maximize** | window.py | Zoom/fit now correctly preserves center offset when window is maximized or un-maximized. |
| F16 | **Annotations created while zoomed appear wrong size** | canvas.py | `_tool_scroll_for_pos` now returns `_draw_y` (includes `_center_y`) instead of just `_scroll_y`, fixing screen-to-page coordinate conversion at all zoom levels. |
| F17 | **Annotations need resize handles** | select_tool.py | Selected annotations now show 8 draggable handles (4 corners + 4 edges). Drag any handle to resize. Press Escape to cancel. |
| F18 | **Continuous mode page indicator not updating** | canvas.py | Added `page-changed` signal to canvas, fires when scroll position changes the current page. |
| F19 | **Continuous mode scroll too slow** | canvas.py | Added `SCROLL_SPEED` multiplier (15x). |
| F20 | **Continuous mode scroll direction reversed** | canvas.py | Fixed sign on `_scroll_y` delta. |
| F21 | **Segfault selecting annotations** | select_tool.py | `_find_annot_at` now returns `(page, annot)` tuple to keep the Python Page wrapper alive. |
| F22 | **Properties panel hidden** | window.py | Clicking Callout / Shape / Line / Highlight toolbar buttons now auto-opens a tool-specific config popover with OK/Cancel. |
| F23 | **Highlight tint hardcoded** | highlight_tool.py | Highlight tool now reads `highlight_tint` from properties, selectable in the config popover. |
| F24 | **Scroll direction inverted in single-page mode** | `canvas.py:510-513` | In `_on_scroll`, single-page mode now negates the scroll delta (`-=` instead of `+=`) so content moves in the correct direction. |
| F25 | **SCROLL_SPEED too slow** | `canvas.py:13` | Increased from 15 to 55. |
| F26 | **Canvas delete handler doesn't delegate to active tool** | `canvas.py:552-554` | Now calls `self._active_tool.on_delete()` first; if the tool handles it, the canvas skips its own delete logic. Added `on_delete()` method to `SelectTool` that delegates to `delete_selected()`. |
| F27 | **White page background hardcoded in dark mode** | `canvas.py:354-358, 415-419` | Single-page and continuous mode both check `_is_dark()` and use `rgb(0.2,0.2,0.2)` in dark mode instead of hardcoded white. |
| F28 | **Zoom-fit never calculated (broken retry logic)** | `window.py:852-877` | Original retry-compare pattern stored stale allocation on first call and immediately compared equal to itself, looping 200 times without ever computing the zoom. Replaced with `GLib.timeout_add(200, ...)` — waits for compositor, then fits once on the correct allocation. |
| F29 | **Scroll clamp allowed scrolling past page top** | `canvas.py:509` | Fixed clamp formula from `max(-max, min(max, scroll_y))` to `min(0, max(-max, scroll_y))`. After scroll-direction fix, `scroll_y=0` = top of page. Old clamp allowed positive scroll past the top. |
| F30 | **image_tool accesses private `_scroll_x/_scroll_y`** | `canvas.py:231-236`, `image_tool.py:156` | Renamed `_draw_x`/`_draw_y` properties to public `draw_x`/`draw_y`. Updated `image_tool.py` to use them. |
| F31 | **Missing `clean_contents()` in cut_tool** | `cut_tool.py:52` | Added `page.clean_contents()` after `apply_redactions()`. |
| F32 | **Continuous scroll button wrong highlight color** | `style.css:37-41` | Added `.chisel-navbox button:checked` with `background: alpha(@accent_bg_color, 0.25)` matching the toolbox button checked style. |
| F33 | **Window snap doesn't auto-fit zoom** | `window.py:469, 854-869` | Added `size-allocate` handler on canvas with 300ms debounce and 50px change threshold. Triggers zoom-fit on snap, tile, maximize, and drag-resize. |
| F34 | **Fraction editor, text editor, image insert falsely listed as broken** | (diagnosis) | Ran end-to-end runtime tests: all three tools are fully functional. Text editor finds spans and shows overlay entries; fraction editor detects and selects fractions; image tool opens file dialog. Removed from active-issues list. |
| F35 | **App crashes on startup: `size-allocate` is not a GTK4 signal** | `window.py:469` | Replaced `canvas.connect("size-allocate", ...)` with `self.connect("notify::default-width", ...)` and `self.connect("notify::default-height", ...)`. The `size-allocate` signal was removed in GTK4. |
