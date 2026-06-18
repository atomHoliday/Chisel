from tools.base import Tool
from drawing.overlay import draw_preview_callout
from drawing.callout import draw_callout_on_page


class CalloutTool(Tool):
    name = "callout"

    def __init__(self, canvas, document, props):
        super().__init__(canvas, document)
        self._props = props
        self._origin = None
        self._current = None
        self._is_dragging = False
        self._mode = None

    def activate(self):
        self._origin = None
        self._current = None
        self._is_dragging = False
        self._mode = None
        self._canvas.queue_draw()

    def deactivate(self):
        self._origin = None
        self._current = None
        self._is_dragging = False
        self._mode = None
        self._canvas.queue_draw()

    def on_drag_begin(self, x, y, scale, scroll_x, scroll_y):
        px, py = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        self._origin = (px, py)
        self._current = (px, py)
        self._is_dragging = True
        self._mode = "leader"
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
            box_w = 120
            box_h = 40
            bx0 = cx
            by0 = cy - box_h / 2
            bx1 = cx + box_w
            by1 = cy + box_h / 2
            page = doc._doc[self._canvas.page_num]
            color = self._props.get("stroke_color", (0, 0, 0))
            width = self._props.get("stroke_width", 1)
            text = self._props.get("callout_text", "")
            draw_callout_on_page(page, bx0, by0, bx1, by1, ox, oy,
                                 color=color, width=width, text=text)
            self._canvas._pixbuf = None
            self._canvas.queue_draw()
        self._reset()
        return True

    def _reset(self):
        self._origin = None
        self._current = None
        self._is_dragging = False
        self._mode = None

    def draw_overlay(self, cr, width, height, scale, scroll_x, scroll_y):
        if self._is_dragging and self._origin and self._current:
            ox, oy = self._origin
            cx, cy = self._current
            oxs = ox * scale + scroll_x
            oys = oy * scale + scroll_y
            cxs = cx * scale + scroll_x
            cys = cy * scale + scroll_y
            box_w = 120 * scale
            box_h = 40 * scale
            color = self._props.get("stroke_color", (0, 0, 0))
            width = self._props.get("stroke_width", 1)
            draw_preview_callout(cr, cxs, cys - box_h / 2, cxs + box_w, cys + box_h / 2,
                                 oxs, oys, color=color, width=width)
