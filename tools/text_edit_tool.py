import sys
from gi.repository import Gtk, Gdk, Adw

from tools.base import Tool
from document.text_model import find_span_at
from tools.fraction_edit_tool import _builtin_font

print("[TEXT_TOOL] module loaded", file=sys.stderr)

_CSS = """
.text-tool-entry {
    background: @theme_base_color;
    color: @theme_text_color;
    border: 1px solid @borders;
    border-radius: 4px;
    padding: 2px 4px;
    font-family: monospace;
}
"""


class TextEditTool(Tool):
    name = "text_edit"

    def __init__(self, canvas, document, overlay, toast_overlay):
        super().__init__(canvas, document)
        self._overlay = overlay
        self._toast_overlay = toast_overlay
        self._entry = None
        self._editing_span = None
        self._page_num = -1
        self._ensure_css()

    def activate(self):
        print("[TEXT_TOOL] activate", file=sys.stderr)
        self._remove_entry()

    def deactivate(self):
        print("[TEXT_TOOL] deactivate", file=sys.stderr)
        self._remove_entry()

    def on_click(self, x, y, scale, scroll_x, scroll_y):
        page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        print(f"[TEXT_TOOL] on_click: screen({x:.1f},{y:.1f}) page({page_x:.1f},{page_y:.1f}) scale={scale:.2f}", file=sys.stderr)
        doc = self._document
        if not doc or not doc.is_loaded:
            print("[TEXT_TOOL] no document loaded", file=sys.stderr)
            return False
        page_num = self._canvas.page_num
        span = find_span_at(doc, page_num, page_x, page_y)
        if span is None:
            print(f"[TEXT_TOOL] no span found at ({page_x:.1f},{page_y:.1f})", file=sys.stderr)
            self._remove_entry()
            return False
        print(f"[TEXT_TOOL] found span: text={span.text!r}, bbox={span.bbox}, font={span.font_name!r}, size={span.font_size}", file=sys.stderr)
        self._page_num = page_num
        self._show_entry(span, scale, scroll_x, scroll_y)
        return True

    def _remove_entry(self, *args):
        print(f"[TEXT_TOOL] _remove_entry (entry was {self._entry is not None})", file=sys.stderr)
        if self._entry is not None:
            self._overlay.remove_overlay(self._entry)
            self._entry = None
        self._editing_span = None

    def _ensure_css(self):
        if not hasattr(TextEditTool, '_css_provider'):
            provider = Gtk.CssProvider()
            provider.load_from_string(_CSS)
            TextEditTool._css_provider = provider
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _show_entry(self, span, scale, scroll_x, scroll_y):
        self._remove_entry()
        self._editing_span = span

        bx0, by0, bx1, by1 = span.bbox
        x = bx0 * scale + scroll_x
        y = by0 * scale + scroll_y
        w = (bx1 - bx0) * scale + 10
        h = (by1 - by0) * scale + 10
        print(f"[TEXT_TOOL] _show_entry: screen_pos=({x:.1f},{y:.1f}) size=({w:.1f},{h:.1f}) text={span.text!r}", file=sys.stderr)

        self._entry = Gtk.Entry()
        self._entry.set_halign(Gtk.Align.START)
        self._entry.set_valign(Gtk.Align.START)
        self._entry.set_text(span.text)
        self._entry.set_size_request(int(max(w, 50)), int(max(h, 30)))
        self._entry.add_css_class("text-tool-entry")
        self._entry.set_has_frame(False)
        self._entry.connect("activate", self._on_entry_activate)
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_entry_key)
        self._entry.add_controller(controller)

        self._overlay.add_overlay(self._entry)
        self._entry.set_margin_start(int(x))
        self._entry.set_margin_top(int(y))
        self._entry.grab_focus()

    def _on_entry_activate(self, entry):
        print(f"[TEXT_TOOL] _on_entry_activate: entry text={entry.get_text()!r}", file=sys.stderr)
        self._apply_edit()
        self._remove_entry()

    def _on_entry_key(self, controller, keyval, keycode, state):
        print(f"[TEXT_TOOL] key pressed: keyval={keyval}", file=sys.stderr)
        if keyval == Gdk.KEY_Escape:
            self._remove_entry()
            return True
        return False

    def _toast(self, msg):
        if self._toast_overlay:
            self._toast_overlay.add_toast(Adw.Toast.new(msg))

    def _apply_edit(self):
        print("[TEXT_TOOL] _apply_edit called", file=sys.stderr)
        if self._editing_span is None or self._entry is None:
            print("[TEXT_TOOL] _apply_edit: no editing span or entry", file=sys.stderr)
            return
        new_text = self._entry.get_text()
        span = self._editing_span
        print(f"[TEXT_TOOL] _apply_edit: old={span.text!r} -> new={new_text!r}", file=sys.stderr)
        doc = self._document
        if not doc or not doc._doc:
            print("[TEXT_TOOL] _apply_edit: no document", file=sys.stderr)
            return
        if self._page_num != self._canvas.page_num:
            print(f"[TEXT_TOOL] _apply_edit: page mismatch stored={self._page_num} current={self._canvas.page_num}", file=sys.stderr)
            return
        print(f"[TEXT_TOOL] _apply_edit: page_num={self._page_num}, bbox={span.bbox}, origin={span.origin}", file=sys.stderr)
        try:
            page = doc._doc[self._page_num]
            print("[TEXT_TOOL] start journal op", file=sys.stderr)
            doc._doc.journal_start_op("edit text")
            try:
                print("[TEXT_TOOL] adding redact annotation", file=sys.stderr)
                annot = page.add_redact_annot(span.bbox)
                print("[TEXT_TOOL] setting fill to white", file=sys.stderr)
                annot.set_colors(fill=(1, 1, 1))
                print("[TEXT_TOOL] applying redactions", file=sys.stderr)
                page.apply_redactions()
                print("[TEXT_TOOL] cleaning page contents", file=sys.stderr)
                page.clean_contents()
                if new_text:
                    font_name = _builtin_font(span.font_name)
                    print(f"[TEXT_TOOL] font mapping: {span.font_name!r} -> {font_name!r}", file=sys.stderr)
                    print(f"[TEXT_TOOL] insert_text: pos={span.origin}, text={new_text!r}, fontsize={span.font_size}, fontname={font_name!r}, color=(0,0,0)", file=sys.stderr)
                    page.insert_text(
                        (span.origin[0], span.origin[1]),
                        new_text,
                        fontsize=span.font_size,
                        fontname=font_name,
                        color=(0, 0, 0),
                    )
                else:
                    print("[TEXT_TOOL] new_text is empty, skipping insert_text", file=sys.stderr)
            finally:
                doc._doc.journal_stop_op()
            self._toast("Text updated")
        except Exception as e:
            print(f"[TEXT_TOOL] ERROR in _apply_edit: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            self._toast(f"Error: {e}")
        print("[TEXT_TOOL] invalidating pixbuf and queueing redraw", file=sys.stderr)
        self._canvas._pixbuf = None
        self._canvas.queue_draw()
