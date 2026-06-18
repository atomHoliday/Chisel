import pymupdf
from tools.base import Tool
from drawing.overlay import draw_preview_rect, draw_preview_circle


class ShapeTool(Tool):
    name = "shape"

    def __init__(self, canvas, document, props):
        super().__init__(canvas, document)
        self._props = props
        self._start = None
        self._end = None
        self._is_dragging = False

    def activate(self):
        self._start = None
        self._end = None
        self._is_dragging = False
        self._canvas.queue_draw()

    def deactivate(self):
        self._start = None
        self._end = None
        self._is_dragging = False
        self._canvas.queue_draw()

    def on_drag_begin(self, x, y, scale, scroll_x, scroll_y):
        px, py = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        self._start = (px, py)
        self._is_dragging = True
        return True

    def on_drag_update(self, x, y, scale, scroll_x, scroll_y):
        if self._is_dragging and self._start:
            px, py = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
            self._end = (px, py)
            self._canvas.queue_draw()
            return True
        return False

    def on_drag_end(self, x, y, scale, scroll_x, scroll_y):
        if self._is_dragging and self._start and self._end:
            sx, sy = self._start
            ex, ey = self._end
            doc = self._document
            if doc and doc._doc:
                page = doc._doc[self._canvas.page_num]
                color = self._props.get("stroke_color", (0, 0, 0))
                width = self._props.get("stroke_width", 1)
                fill = self._props.get("fill_color", None)
                shape_type = self._props.get("shape_type", "rectangle")
                rect = (min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey))

                if shape_type == "circle":
                    annot = page.add_circle_annot(rect)
                else:
                    annot = page.add_rect_annot(rect)

                annot.set_colors(stroke=color, fill=fill)
                annot.set_border(width=width)
                annot.update()
                if fill:
                    annot.set_opacity(0.3)

                self._canvas._pixbuf = None
                self._canvas.queue_draw()
        self._start = None
        self._end = None
        self._is_dragging = False
        return True

    def draw_overlay(self, cr, width, height, scale, scroll_x, scroll_y):
        if self._is_dragging and self._start and self._end:
            sx, sy = self._start
            ex, ey = self._end
            color = self._props.get("stroke_color", (0, 0, 0))
            w = self._props.get("stroke_width", 1)
            fill = self._props.get("fill_color", None)
            x0 = min(sx, ex) * scale + scroll_x
            y0 = min(sy, ey) * scale + scroll_y
            x1 = max(sx, ex) * scale + scroll_x
            y1 = max(sy, ey) * scale + scroll_y
            shape_type = self._props.get("shape_type", "rectangle")
            if shape_type == "circle":
                cx = (x0 + x1) / 2
                cy = (y0 + y1) / 2
                r = max(x1 - x0, y1 - y0) / 2
                draw_preview_circle(cr, cx, cy, r, color=color, width=w, fill=fill)
            else:
                draw_preview_rect(cr, x0, y0, x1, y1, color=color, width=w, fill=fill)
