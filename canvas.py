import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf
from gi.repository import cairo


CLICK_THRESHOLD = 8


class PdfCanvas(Gtk.DrawingArea):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._document = None
        self._page_num = 0
        self._scale = 1.0
        self._scroll_x = 0.0
        self._scroll_y = 0.0
        self._press_pos = None
        self._drag_start_scroll = None
        self._pixbuf = None
        self._active_tool = None
        self._tool_is_dragging = False
        self._is_pressed = False
        self._has_moved = False
        self._ctrl_held = False

        self.set_vexpand(True)
        self.set_hexpand(True)

        self.set_draw_func(self._on_draw)
        self._connect_gestures()

    def _connect_gestures(self):
        scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )
        scroll.connect("scroll", self._on_scroll)
        self.add_controller(scroll)

        click = Gtk.GestureClick.new()
        click.connect("pressed", self._on_click_pressed)
        click.connect("released", self._on_click_released)
        self.add_controller(click)

        motion = Gtk.EventControllerMotion.new()
        motion.connect("motion", self._on_motion)
        self.add_controller(motion)

        keys = Gtk.EventControllerKey.new()
        keys.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keys)

        self.set_focusable(True)
        self.set_can_focus(True)

    def set_active_tool(self, tool):
        if self._active_tool:
            self._active_tool.deactivate()
        self._active_tool = tool
        if tool:
            tool.activate()
        self.queue_draw()

    @property
    def active_tool(self):
        return self._active_tool

    def set_document(self, document):
        self._document = document
        self._page_num = 0
        self._scale = 1.0
        self._scroll_x = 0.0
        self._scroll_y = 0.0
        self._pixbuf = None
        self.queue_draw()

    def set_page(self, page_num):
        if not self._document:
            return
        self._page_num = max(0, min(page_num, self._document.page_count - 1))
        self._scroll_x = 0.0
        self._scroll_y = 0.0
        self._pixbuf = None
        self.queue_draw()

    def _get_pixbuf(self):
        if self._pixbuf is not None:
            return self._pixbuf
        if not self._document or not self._document.is_loaded:
            return None
        png_data, w, h = self._document.render_page(self._page_num, self._scale)
        stream = GdkPixbuf.PixbufLoader.new_with_mime_type("image/png")
        stream.write(png_data)
        stream.close()
        self._pixbuf = stream.get_pixbuf()
        return self._pixbuf

    def _on_draw(self, area, cr, w, h):
        cr.set_source_rgb(0.85, 0.85, 0.85)
        cr.paint()

        if not self._document or not self._document.is_loaded:
            cr.set_source_rgb(0.6, 0.6, 0.6)
            cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)
            cr.set_font_size(18)
            cr.move_to(w / 2 - 80, h / 2)
            cr.show_text("No PDF loaded")
            return

        pixbuf = self._get_pixbuf()
        if pixbuf is None:
            return

        disp_w = pixbuf.get_width()
        disp_h = pixbuf.get_height()

        cr.translate(self._scroll_x, self._scroll_y)

        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, disp_w, disp_h)
        cr.fill()

        Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
        cr.paint()

        cr.translate(-self._scroll_x, -self._scroll_y)

        if self._active_tool:
            self._active_tool.draw_overlay(
                cr, w, h, self._scale, self._scroll_x, self._scroll_y
            )

    def _on_click_pressed(self, gesture, n_press, x, y):
        self._press_pos = (x, y)
        self._drag_start_scroll = (self._scroll_x, self._scroll_y)
        self._is_pressed = True
        self._has_moved = False
        self._ctrl_held = bool(gesture.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK)
        if self._ctrl_held or self._active_tool is None:
            self._tool_is_dragging = False
        else:
            self._tool_is_dragging = self._active_tool.on_drag_begin(
                x, y, self._scale, self._scroll_x, self._scroll_y
            )

    def _on_motion(self, controller, x, y):
        if not self._is_pressed:
            return
        dx = x - self._press_pos[0]
        dy = y - self._press_pos[1]
        if dx * dx + dy * dy < CLICK_THRESHOLD * CLICK_THRESHOLD:
            return
        self._has_moved = True
        if self._tool_is_dragging and self._active_tool:
            self._active_tool.on_drag_update(
                x, y, self._scale, self._scroll_x, self._scroll_y
            )
        elif self._ctrl_held or self._active_tool is None:
            self._scroll_x = self._drag_start_scroll[0] - dx
            self._scroll_y = self._drag_start_scroll[1] - dy
            self.queue_draw()

    def _on_click_released(self, gesture, n_press, x, y):
        if not self._is_pressed:
            return
        dx = x - self._press_pos[0]
        dy = y - self._press_pos[1]
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < CLICK_THRESHOLD and self._active_tool:
            self._active_tool.on_click(
                self._press_pos[0], self._press_pos[1],
                self._scale, self._scroll_x, self._scroll_y
            )
        elif self._has_moved and self._tool_is_dragging and self._active_tool:
            self._active_tool.on_drag_end(
                x, y, self._scale, self._scroll_x, self._scroll_y
            )
        self.grab_focus()
        self._is_pressed = False
        self._has_moved = False
        self._ctrl_held = False
        self._press_pos = None
        self._drag_start_scroll = None
        self._tool_is_dragging = False

    def _on_scroll(self, controller, dx, dy):
        if not self._document:
            return False
        state = controller.get_current_event_state()
        if state & Gdk.ModifierType.CONTROL_MASK:
            self._scale *= 1.1 if dy < 0 else 0.9
            self._scale = max(0.1, min(10.0, self._scale))
            self._pixbuf = None
            self.queue_draw()
        else:
            self._scroll_y -= dy
            self.queue_draw()
        return True

    def _on_key_pressed(self, controller, keyval, keycode, state):
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        if ctrl and keyval == Gdk.KEY_v:
            if self._active_tool:
                self._active_tool.on_paste()
            return True
        if not self._document:
            return False
        if keyval == Gdk.KEY_plus or keyval == Gdk.KEY_equal:
            self._scale *= 1.2
            self._scale = min(10.0, self._scale)
            self._pixbuf = None
            self.queue_draw()
            return True
        elif keyval == Gdk.KEY_minus:
            self._scale *= 0.8
            self._scale = max(0.1, self._scale)
            self._pixbuf = None
            self.queue_draw()
            return True
        elif keyval == Gdk.KEY_Page_Down:
            self.set_page(self._page_num + 1)
            return True
        elif keyval == Gdk.KEY_Page_Up:
            self.set_page(self._page_num - 1)
            return True
        elif keyval == Gdk.KEY_Home:
            self.set_page(0)
            return True
        elif keyval == Gdk.KEY_End:
            self.set_page(self._document.page_count - 1)
            return True
        return False

    @property
    def page_num(self):
        return self._page_num

    @property
    def scale(self):
        return self._scale
