from tools.base import Tool


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
            if doc and doc._doc:
                page = doc._doc[self._canvas.page_num]
                rect = (min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey))
                doc._doc.journal_start_op("add highlight")
                try:
                    page.add_highlight_annot(rect)
                finally:
                    doc._doc.journal_stop_op()
                self._canvas._pixbuf = None
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
            cr.save()
            cr.set_source_rgba(1, 1, 0, 0.3)
            cr.rectangle(x, y, w, h)
            cr.fill()
            cr.set_source_rgba(1, 0.8, 0, 0.8)
            cr.set_line_width(1.5)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            cr.restore()
