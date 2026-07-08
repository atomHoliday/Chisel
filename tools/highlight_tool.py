from tools.base import Tool
from drawing.theme import HIGHLIGHT_WIDTH


class HighlightTool(Tool):
    name = "highlight"

    def __init__(self, canvas, document, props):
        super().__init__(canvas, document)
        self._props = props
        self._drag_start = None
        self._drag_end = None
        self._is_dragging = False

    def activate(self):
        self._drag_start = None
        self._drag_end = None
        self._is_dragging = False
        self._canvas.queue_draw()

    def deactivate(self):
        self._drag_start = None
        self._drag_end = None
        self._is_dragging = False
        self._canvas.queue_draw()

    def on_drag_begin(self, x, y, scale, scroll_x, scroll_y):
        px, py = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        self._drag_start = (px, py)
        self._is_dragging = True
        return True

    def on_drag_update(self, x, y, scale, scroll_x, scroll_y):
        if self._is_dragging and self._drag_start:
            px, py = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
            self._drag_end = (px, py)
            self._canvas.queue_draw()
            return True
        return False

    def on_drag_end(self, x, y, scale, scroll_x, scroll_y):
        if self._is_dragging and self._drag_start and self._drag_end:
            sx, sy = self._drag_start
            ex, ey = self._drag_end
            doc = self._document
            if doc and doc.doc:
                page = doc.doc[self._canvas.page_num]
                rect = (min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey))
                tint = self._props.get("highlight_tint", (1.0, 0.8, 0.0))
                doc.doc.journal_start_op("add highlight")
                try:
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=tint)
                    annot.update()
                finally:
                    doc.doc.journal_stop_op()
                self._canvas.invalidate_cache()
                self._canvas.invalidate_page_cache(self._canvas.page_num)
                self._canvas.queue_draw()
        self._drag_start = None
        self._drag_end = None
        self._is_dragging = False
        return True

    def draw_overlay(self, cr, width, height, scale, scroll_x, scroll_y):
        if self._is_dragging and self._drag_start and self._drag_end:
            sx, sy = self._drag_start
            ex, ey = self._drag_end
            x = min(sx, ex) * scale + scroll_x
            y = min(sy, ey) * scale + scroll_y
            w = abs(ex - sx) * scale
            h = abs(ey - sy) * scale
            tint = self._props.get("highlight_tint", (1.0, 0.8, 0.0))
            cr.save()
            cr.set_source_rgba(tint[0], tint[1], tint[2], 0.3)
            cr.rectangle(x, y, w, h)
            cr.fill()
            cr.set_source_rgba(tint[0], tint[1], tint[2], 0.6)
            cr.set_line_width(HIGHLIGHT_WIDTH)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            cr.restore()
