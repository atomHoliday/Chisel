class Tool:
    name = "tool"

    def __init__(self, canvas, document):
        self._canvas = canvas
        self._document = document

    def activate(self):
        pass

    def deactivate(self):
        pass

    def on_click(self, x, y, scale, scroll_x, scroll_y):
        return False

    def on_drag_begin(self, x, y, scale, scroll_x, scroll_y):
        return False

    def on_drag_update(self, x, y, scale, scroll_x, scroll_y):
        return False

    def on_drag_end(self, x, y, scale, scroll_x, scroll_y):
        return False

    def on_motion(self, x, y, scale, scroll_x, scroll_y):
        return False

    def on_paste(self):
        return False

    def on_copy(self):
        return False

    def on_delete(self):
        return False

    def on_escape(self):
        return False

    def draw_overlay(self, cr, width, height, scale, scroll_x, scroll_y):
        pass

    def canvas_to_page(self, cx, cy, scale, draw_x, draw_y):
        return (cx - draw_x) / scale, (cy - draw_y) / scale
