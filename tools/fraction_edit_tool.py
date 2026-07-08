import sys
from gi.repository import Gtk, Gdk, Adw

from tools.base import Tool
from document.fraction_detector import detect_fractions, find_fraction_at
from drawing.theme import (
    FRACTION_SELECTED_FILL, FRACTION_SELECTED_BORDER,
    FRACTION_UNSELECTED_FILL, FRACTION_UNSELECTED_BORDER,
    FRACTION_LABEL_COLOR, FRACTION_WIDTH,
)

_BUILTIN_FONTS = {
    "helv", "helvetica", "tiro", "times", "cour", "courier",
    "symb", "symbol", "zadb", "zapfdingbats",
    "cobo", "cobao", "coboo", "copo",
}


def _builtin_font(font_name):
    name = font_name.lower().replace(" ", "")

    if name.endswith("mt"):
        name = name[:-2]

    parts = name.rsplit("-", 1)
    base_part = parts[0]
    style_part = parts[1] if len(parts) > 1 else ""

    if style_part not in ("bold", "italic", "oblique", "bolditalic", "boldoblique"):
        style_part = ""

    font_groups = [
        (["helv", "helvetica", "arial"], "Helvetica", {"italic": "Oblique", "bolditalic": "BoldOblique"}),
        (["cour", "courier", "couriernew"], "Courier", {"italic": "Oblique", "bolditalic": "BoldOblique"}),
        (["tiro", "times", "timesroman", "timesnewroman"], ("Times-Roman", "Times"), {"italic": "Italic", "bolditalic": "BoldItalic"}),
    ]

    style_map = {
        "bold": "Bold", "italic": "Italic", "oblique": "Oblique",
        "bolditalic": "BoldItalic", "boldoblique": "BoldOblique",
    }

    for prefixes, pdf_name, style_overrides in font_groups:
        if base_part in prefixes or any(base_part.startswith(p) for p in prefixes):
            mapped_style = style_overrides.get(style_part, style_map.get(style_part, ""))
            if isinstance(pdf_name, tuple):
                base_regular, base_styled = pdf_name
                if mapped_style:
                    return f"{base_styled}-{mapped_style}"
                return base_regular
            if mapped_style:
                return f"{pdf_name}-{mapped_style}"
            return pdf_name

    fallback_style = style_map.get(style_part, "")
    if fallback_style:
        return f"Helvetica-{fallback_style}"
    return "Helvetica"


class FractionEditTool(Tool):
    name = "fraction"

    def __init__(self, canvas, document, overlay, toast_overlay):
        super().__init__(canvas, document)
        self._overlay = overlay
        self._toast_overlay = toast_overlay
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
            popover.popdown()
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
        if not doc or not doc.doc:
            return
        if self._page_num != self._canvas.page_num:
            return

        try:
            page = doc.doc[self._page_num]

            # Capture vector drawings that overlap the fraction area
            fx0, fy0, fx1, fy1 = frac.bbox
            captured = []
            for d in page.get_drawings():
                dr = d["rect"]
                if dr.x0 < fx1 and dr.x1 > fx0 and dr.y0 < fy1 and dr.y1 > fy0:
                    captured.append({
                        "items": d["items"],
                        "color": d.get("color", (0, 0, 0)),
                        "width": d.get("width", 0),
                        "fill": d.get("fill"),
                        "dashes": d.get("dashes"),
                        "lineCap": d.get("lineCap"),
                        "lineJoin": d.get("lineJoin"),
                        "closePath": d.get("closePath", True),
                        "stroke_opacity": d.get("stroke_opacity", 1),
                        "fill_opacity": d.get("fill_opacity", 1),
                    })
            print(f"[FRAC] captured {len(captured)} drawings to re-draw", file=sys.stderr)
            doc.doc.journal_start_op("edit fraction")
            try:
                page.add_redact_annot(frac.bbox).set_colors(fill=(1, 1, 1))
                page.apply_redactions()
                page.clean_contents()

                font_size = frac.font_size or 14
                font_name = _builtin_font(frac.font_name or "helv")
                offset = font_size * 0.15

                if new_num:
                    nb = frac.num_bbox or frac.bbox
                    num_pos = frac.num_origin or (nb[0], nb[3])
                    num_pos = (num_pos[0], num_pos[1] - offset)
                    page.insert_text(
                        (num_pos[0], num_pos[1]),
                        new_num,
                        fontsize=font_size,
                        fontname=font_name,
                        color=(0, 0, 0),
                    )
                if new_den:
                    db = frac.den_bbox or frac.bbox
                    den_pos = frac.den_origin or (db[0], db[3])
                    den_pos = (den_pos[0], den_pos[1] + offset)
                    page.insert_text(
                        (den_pos[0], den_pos[1]),
                        new_den,
                        fontsize=font_size,
                        fontname=font_name,
                        color=(0, 0, 0),
                    )

                # Re-draw captured vector lines (so they aren't erased by redaction)
                for cap in captured:
                    shape = page.new_shape()
                    for item in cap["items"]:
                        cmd = item[0]
                        if cmd == "l":
                            shape.draw_line(item[1], item[2])
                        elif cmd == "re":
                            shape.draw_rect(item[1])
                        elif cmd == "qu":
                            shape.draw_quad(item[1])
                        elif cmd == "cur":
                            shape.draw_bezier(item[1], item[2], item[3], item[4])
                    kw = dict(
                        width=cap["width"],
                        color=cap["color"],
                        fill=cap["fill"],
                        closePath=cap["closePath"],
                        dashes=cap["dashes"],
                        lineCap=cap["lineCap"],
                        lineJoin=cap["lineJoin"],
                    )
                    if cap["stroke_opacity"] is not None:
                        kw["stroke_opacity"] = cap["stroke_opacity"]
                    if cap["fill_opacity"] is not None:
                        kw["fill_opacity"] = cap["fill_opacity"]
                    shape.finish(**kw)
                    shape.commit()
            finally:
                doc.doc.journal_stop_op()

            if self._toast_overlay:
                self._toast_overlay.add_toast(Adw.Toast.new("Fraction updated"))
        except Exception:
            import traceback
            traceback.print_exc()
            if self._toast_overlay:
                self._toast_overlay.add_toast(Adw.Toast.new("Error updating fraction"))
            self._close_popover()
            return

        self._close_popover()
        self._selected_fraction = None
        self._refresh_fractions()
        self._canvas.invalidate_cache()
        self._canvas.invalidate_page_cache(self._canvas.page_num)
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
                cr.set_source_rgba(*FRACTION_SELECTED_FILL)
            else:
                cr.set_source_rgba(*FRACTION_UNSELECTED_FILL)

            cr.rectangle(x, y, w, h)
            cr.fill()

            if is_selected:
                cr.set_source_rgba(*FRACTION_SELECTED_BORDER)
            else:
                cr.set_source_rgba(*FRACTION_UNSELECTED_BORDER)

            cr.set_line_width(FRACTION_WIDTH)
            cr.rectangle(x, y, w, h)
            cr.stroke()

            label = f"{frac.numerator_text}/{frac.denominator_text}"
            cr.set_font_size(10)
            cr.set_source_rgb(*FRACTION_LABEL_COLOR)
            cr.move_to(x + 2, y - 4)
            cr.show_text(label)
