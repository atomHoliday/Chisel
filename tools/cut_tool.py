from tools.base import Tool
from drawing.theme import CUT_FILL, CUT_BORDER, CUT_WIDTH


class CutTool(Tool):
    name = "cut"

    def __init__(self, canvas, document):
        super().__init__(canvas, document)
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
                doc.doc.journal_start_op("cut")
                try:
                    page.add_redact_annot(rect)
                    page.apply_redactions()
                    page.clean_contents()
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
            cr.save()
            cr.set_source_rgba(*CUT_FILL)
            cr.rectangle(x, y, w, h)
            cr.fill()
            cr.set_source_rgba(*CUT_BORDER)
            cr.set_line_width(CUT_WIDTH)
            cr.set_dash([6, 4], 0)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            cr.set_dash([], 0)
            cr.restore()
