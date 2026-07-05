import pymupdf
from tools.base import Tool
from drawing.overlay import draw_preview_line, draw_preview_arrow


class LineTool(Tool):
    name = "line"

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
                is_arrow = self._props.get("has_arrow", False)

                doc._doc.journal_start_op("add line")
                try:
                    annot = page.add_line_annot((sx, sy), (ex, ey))
                    annot.set_colors(stroke=color)
                    annot.set_border(width=width)
                    if is_arrow:
                        annot.set_line_ends(
                            pymupdf.PDF_ANNOT_LE_OPEN_ARROW,
                            pymupdf.PDF_ANNOT_LE_NONE,
                        )
                    annot.update()
                finally:
                    doc._doc.journal_stop_op()

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
            x0 = sx * scale + scroll_x
            y0 = sy * scale + scroll_y
            x1 = ex * scale + scroll_x
            y1 = ey * scale + scroll_y
            color = self._props.get("stroke_color", (0, 0, 0))
            w = self._props.get("stroke_width", 1)
            if self._props.get("has_arrow", False):
                draw_preview_arrow(cr, x0, y0, x1, y1, color=color, width=w)
            else:
                draw_preview_line(cr, x0, y0, x1, y1, color=color, width=w)
