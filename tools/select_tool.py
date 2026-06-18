from tools.base import Tool
from document.text_model import find_span_at


class SelectTool(Tool):
    name = "select"

    def __init__(self, canvas, document):
        super().__init__(canvas, document)
        self._selected_span = None
        self._page_num = -1

    def activate(self):
        self._selected_span = None
        self._page_num = -1
        self._canvas.queue_draw()

    def deactivate(self):
        self._selected_span = None
        self._page_num = -1
        self._canvas.queue_draw()

    def on_click(self, x, y, scale, scroll_x, scroll_y):
        page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        doc = self._document
        if not doc or not doc.is_loaded:
            return False
        page_num = self._canvas.page_num
        span = find_span_at(doc, page_num, page_x, page_y)
        self._selected_span = span
        self._page_num = page_num
        self._canvas.queue_draw()
        return True

    def draw_overlay(self, cr, width, height, scale, scroll_x, scroll_y):
        if self._selected_span is None or self._page_num != self._canvas.page_num:
            return
        bbox = self._selected_span.bbox
        x = bbox[0] * scale + scroll_x
        y = bbox[1] * scale + scroll_y
        w = (bbox[2] - bbox[0]) * scale
        h = (bbox[3] - bbox[1]) * scale

        cr.save()
        cr.set_source_rgba(0.3, 0.6, 1.0, 0.25)
        cr.rectangle(x, y, w, h)
        cr.fill()
        cr.set_source_rgba(0.3, 0.6, 1.0, 0.8)
        cr.set_line_width(1.5)
        cr.rectangle(x, y, w, h)
        cr.stroke()
        cr.restore()

    @property
    def selected_span(self):
        return self._selected_span
