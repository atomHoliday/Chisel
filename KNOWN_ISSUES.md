# Known Issues

## Active

- **Page scale breaks on maximize** — zoom level / fit resets incorrectly when the window is maximized or un-maximized.
- **Snap-to-side tiling cuts off window** — snapping the app to a screen edge via GNOME tiling leaves the window clipped.
- **Annotations need resize handles** — after selecting an annotation, there are no draggable corner/edge handles to resize it. Current workaround: delete and recreate.
- **Annotations created while zoomed appear wrong size** — screen-to-page coordinate conversion may be off when scale != 1.0, producing annotations that are too large or too small relative to the page.

## Fixed

- **Segfault selecting annotations** — `_find_annot_at` now returns `(page, annot)` tuple to keep the Python Page wrapper alive. Prevents "annotation not bound to any page" crash.
- **Properties panel hidden** — clicking Callout / Shape / Line / Highlight toolbar buttons now auto-opens a tool-specific config popover with OK/Cancel. Default startup tool is now SelectTool instead of Pan.
- **Highlight tint hardcoded** — highlight tool now reads `highlight_tint` from properties, selectable in the config popover.
