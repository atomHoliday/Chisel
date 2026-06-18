import pymupdf
from tools.base import Tool
from tools.fraction_edit_tool import _builtin_font
from drawing.overlay import draw_preview_callout, _compute_box, _edge_point


class CalloutTool(Tool):
    name = "callout"

    def __init__(self, canvas, document, props):
        super().__init__(canvas, document)
        self._props = props
        self._origin = None
        self._current = None
        self._is_dragging = False

    def activate(self):
        self._origin = None
        self._current = None
        self._is_dragging = False
        self._canvas.queue_draw()

    def deactivate(self):
        self._origin = None
        self._current = None
        self._is_dragging = False
        self._canvas.queue_draw()

    def on_drag_begin(self, x, y, scale, scroll_x, scroll_y):
        px, py = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        self._origin = (px, py)
        self._current = (px, py)
        self._is_dragging = True
        return True

    def on_drag_update(self, x, y, scale, scroll_x, scroll_y):
        if self._is_dragging and self._origin:
            px, py = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
            self._current = (px, py)
            self._canvas.queue_draw()
            return True
        return False

    def on_drag_end(self, x, y, scale, scroll_x, scroll_y):
        doc = self._document
        if not doc or not doc._doc:
            self._reset()
            return True
        if self._is_dragging and self._origin and self._current:
            ox, oy = self._origin
            cx, cy = self._current
            page = doc._doc[self._canvas.page_num]
            color = self._props.get("stroke_color", (0, 0, 0))
            width = self._props.get("stroke_width", 1)
            text = self._props.get("callout_text", "")

            font_size = 10
            padding = 8
            box_w = max(80, len(text) * font_size * 0.65 + padding * 2)
            box_h = max(50, font_size * 1.5 + padding * 2)
            bx0, by0, bx1, by1 = _compute_box(ox, oy, cx, cy, box_w, box_h)

            # Oval annotation for the outline
            oval = page.add_circle_annot((bx0, by0, bx1, by1))
            oval.set_colors(stroke=color)
            oval.set_border(width=width)
            oval.update()

            # Text rendered directly on page content
            if text:
                bcx = (bx0 + bx1) / 2
                bcy = (by0 + by1) / 2
                text_w = len(text) * font_size * 0.33
                fontname = _builtin_font("Helvetica")
                page.insert_text(
                    (bcx - text_w / 2, bcy + font_size * 0.35),
                    text,
                    fontsize=font_size,
                    fontname=fontname,
                    color=color,
                )

            # Leader line from oval edge to origin, arrow at origin
            ex, ey = _edge_point(bx0, by0, bx1, by1, ox, oy)
            line_annot = page.add_line_annot((ex, ey), (ox, oy))
            line_annot.set_colors(stroke=color)
            line_annot.set_border(width=width)
            line_annot.set_line_ends(pymupdf.PDF_ANNOT_LE_NONE, pymupdf.PDF_ANNOT_LE_OPEN_ARROW)
            line_annot.update()

            # Small filled circle at origin
            dot = page.add_circle_annot((ox - 2, oy - 2, ox + 2, oy + 2))
            dot.set_colors(fill=color)
            dot.set_border(width=0)
            dot.update()

            self._canvas._pixbuf = None
            self._canvas.queue_draw()
        self._reset()
        return True

    def _reset(self):
        self._origin = None
        self._current = None
        self._is_dragging = False

    def draw_overlay(self, cr, width, height, scale, scroll_x, scroll_y):
        if self._is_dragging and self._origin and self._current:
            ox, oy = self._origin
            cx, cy = self._current
            oxs = ox * scale + scroll_x
            oys = oy * scale + scroll_y
            cxs = cx * scale + scroll_x
            cys = cy * scale + scroll_y
            color = self._props.get("stroke_color", (0, 0, 0))
            line_width = self._props.get("stroke_width", 1)
            text = self._props.get("callout_text", "")

            font_size = 10
            padding = 8
            box_w = max(80, len(text) * font_size * 0.65 + padding * 2)
            box_h = max(50, font_size * 1.5 + padding * 2)
            box_w_s = box_w * scale
            box_h_s = box_h * scale

            draw_preview_callout(cr, oxs, oys, cxs, cys, box_w_s, box_h_s,
                                 text, color=color, width=line_width)
