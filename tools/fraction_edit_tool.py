from gi.repository import Gtk, Gdk, Gio

from tools.base import Tool
from document.fraction_detector import detect_fractions, find_fraction_at

_BUILTIN_FONTS = {
    "helv", "helvetica", "tiro", "times", "cour", "courier",
    "symb", "symbol", "zadb", "zapfdingbats",
    "cobo", "cobao", "coboo", "copo",
}


def _builtin_font(font_name):
    name = font_name.lower().replace(" ", "")
    for base_name, variants in {
        "helv": ["helv", "helvetica", "arial", "arialmt"],
        "cour": ["cour", "courier"],
        "tiro": ["tiro", "times", "timesroman"],
    }.items():
        if name in variants:
            return base_name
    return "helv"


class FractionEditTool(Tool):
    name = "fraction"

    def __init__(self, canvas, document, overlay):
        super().__init__(canvas, document)
        self._overlay = overlay
        self._fractions = []
        self._selected_fraction = None
        self._page_num = -1
        self._popover = None
        self._num_entry = None
        self._den_entry = None

    def activate(self):
        self._refresh_fractions()
        self._canvas.queue_draw()

    def deactivate(self):
        self._close_popover()
        self._selected_fraction = None
        self._fractions = []
        self._page_num = -1
        self._canvas.queue_draw()

    def _refresh_fractions(self):
        doc = self._document
        if not doc or not doc.is_loaded:
            self._fractions = []
            return
        page_num = self._canvas.page_num
        self._fractions = detect_fractions(doc, page_num)
        self._page_num = page_num

    def on_click(self, x, y, scale, scroll_x, scroll_y):
        page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        doc = self._document
        if not doc or not doc.is_loaded:
            return False
        page_num = self._canvas.page_num
        if page_num != self._page_num:
            self._refresh_fractions()

        frac = find_fraction_at(doc, page_num, page_x, page_y)
        if frac is None:
            self._close_popover()
            self._selected_fraction = None
            self._canvas.queue_draw()
            return False

        self._selected_fraction = frac
        self._show_popover(x, y, frac)
        self._canvas.queue_draw()
        return True

    def _show_popover(self, screen_x, screen_y, frac):
        self._close_popover()

        self._num_entry = Gtk.Entry()
        self._num_entry.set_text(frac.numerator_text)
        self._num_entry.set_placeholder_text("Numerator")

        self._den_entry = Gtk.Entry()
        self._den_entry.set_text(frac.denominator_text)
        self._den_entry.set_placeholder_text("Denominator")

        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)
        grid.set_margin_start(8)
        grid.set_margin_end(8)

        num_label = Gtk.Label(label="Numerator:")
        num_label.set_halign(Gtk.Align.START)
        grid.attach(num_label, 0, 0, 1, 1)
        grid.attach(self._num_entry, 1, 0, 1, 1)

        den_label = Gtk.Label(label="Denominator:")
        den_label.set_halign(Gtk.Align.START)
        grid.attach(den_label, 0, 1, 1, 1)
        grid.attach(self._den_entry, 1, 1, 1, 1)

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", self._on_apply)
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", self._close_popover)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.append(cancel_btn)
        btn_box.append(apply_btn)
        grid.attach(btn_box, 0, 2, 2, 1)

        self._popover = Gtk.Popover()
        self._popover.set_child(grid)
        self._popover.set_parent(self._canvas)
        rect = Gdk.Rectangle()
        rect.x = int(screen_x)
        rect.y = int(screen_y)
        self._popover.set_pointing_to(rect)
        self._popover.connect("closed", lambda p: self._close_popover())
        self._popover.popup()

    def _close_popover(self, *args):
        popover = self._popover
        self._popover = None
        if popover:
            popover.close()
            popover.unparent()
        self._num_entry = None
        self._den_entry = None

    def _on_apply(self, button):
        if self._selected_fraction is None:
            return
        new_num = self._num_entry.get_text() if self._num_entry else ""
        new_den = self._den_entry.get_text() if self._den_entry else ""
        frac = self._selected_fraction
        doc = self._document
        if not doc or not doc._doc:
            return
        if self._page_num != self._canvas.page_num:
            return

        try:
            page = doc._doc[self._page_num]

            num_bbox = frac.num_bbox or frac.bbox
            den_bbox = frac.den_bbox or frac.bbox
            num_annot = page.add_redact_annot(num_bbox)
            num_annot.set_colors(fill=(1, 1, 1))
            den_annot = page.add_redact_annot(den_bbox)
            den_annot.set_colors(fill=(1, 1, 1))
            page.apply_redactions()
            page.clean_contents()

            font_size = frac.font_size or 14
            font_name = _builtin_font(frac.font_name or "helv")

            if new_num:
                page.insert_text(
                    (num_bbox[0], num_bbox[3]),
                    new_num,
                    fontsize=font_size,
                    fontname=font_name,
                    color=(0, 0, 0),
                )
            if new_den:
                page.insert_text(
                    (den_bbox[0], den_bbox[3]),
                    new_den,
                    fontsize=font_size,
                    fontname=font_name,
                    color=(0, 0, 0),
                )
        except Exception:
            import traceback
            traceback.print_exc()
            self._close_popover()
            return

        self._close_popover()
        self._selected_fraction = None
        self._refresh_fractions()
        self._canvas._pixbuf = None
        self._canvas.queue_draw()

    def draw_overlay(self, cr, width, height, scale, scroll_x, scroll_y):
        if not self._fractions or self._page_num != self._canvas.page_num:
            self._refresh_fractions()

        for frac in self._fractions:
            bx0, by0, bx1, by1 = frac.bbox
            x = bx0 * scale + scroll_x
            y = by0 * scale + scroll_y
            w = (bx1 - bx0) * scale
            h = (by1 - by0) * scale

            is_selected = (
                self._selected_fraction is not None
                and frac.bbox == self._selected_fraction.bbox
            )

            if is_selected:
                cr.set_source_rgba(0.2, 0.8, 0.2, 0.25)
            else:
                cr.set_source_rgba(0.9, 0.6, 0.0, 0.2)

            cr.rectangle(x, y, w, h)
            cr.fill()

            if is_selected:
                cr.set_source_rgba(0.2, 0.8, 0.2, 0.9)
            else:
                cr.set_source_rgba(0.9, 0.6, 0.0, 0.7)

            cr.set_line_width(1.5)
            cr.rectangle(x, y, w, h)
            cr.stroke()

            label = f"{frac.numerator_text}/{frac.denominator_text}"
            cr.set_font_size(10)
            cr.set_source_rgb(0.9, 0.6, 0.0)
            cr.move_to(x + 2, y - 4)
            cr.show_text(label)
