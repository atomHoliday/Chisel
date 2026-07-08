import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, GdkPixbuf, Adw, GObject
from gi.repository import cairo
from gi.repository import GLib
from collections import OrderedDict


CLICK_THRESHOLD = 8
SCROLL_SPEED = 55.0
MAX_CACHE_SIZE = 32

_SHORTCUTS = [
    ("Ctrl+O", "Open PDF"),
    ("Ctrl+S", "Save"),
    ("Ctrl+Shift+S", "Save As"),
    ("Ctrl+Z", "Undo"),
    ("Ctrl+Shift+Z", "Redo"),
    ("Ctrl+C", "Copy selected text/annot"),
    ("Ctrl+V", "Paste"),
    ("Delete", "Delete selected"),
    ("Escape", "Clear selection / Cancel"),
    ("+ / -", "Zoom in / out"),
    ("Ctrl++ / Ctrl+-", "Zoom in / out"),
    ("Ctrl+0", "Zoom to fit"),
    ("Ctrl+scroll", "Zoom"),
    ("Ctrl+drag", "Pan view"),
    ("Page Up / Down", "Navigate pages"),
    ("Home / End", "First / Last page"),
]

_TOOLS = [
    ("Pan", "Default mode. Click+drag to pan."),
    ("Select", "Click to select text or annotations."),
    ("Text Edit", "Click text to edit in place."),
    ("Frac", "Fraction editor — detect and edit fractions."),
    ("Image", "Insert images. Click = file picker, drag = size."),
    ("Highlight", "Drag to highlight region."),
    ("Line", "Drag to draw line or arrow."),
    ("Shape", "Drag to draw rectangle or circle."),
    ("Callout", "Drag from point to create callout box."),
    ("Cut", "Drag to redact (permanently remove) content."),
]


class PdfCanvas(Gtk.DrawingArea):
    __gsignals__ = {
        "page-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._document = None
        self._page_num = 0
        self._scale = 1.0
        self._scroll_x = 0.0
        self._scroll_y = 0.0
        self._center_x = 0.0
        self._center_y = 0.0
        self._press_pos = None
        self._drag_start_scroll = None
        self._pixbuf = None
        self._active_tool = None
        self._tool_is_dragging = False
        self._is_pressed = False
        self._has_moved = False
        self._ctrl_held = False
        self._selected_item = None
        self._continuous = False
        self._page_cache = OrderedDict()
        self._page_offsets = []
        self._last_draw_size = (0, 0)

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
        self.update_property(
            [Gtk.AccessibleProperty.LABEL], ["PDF document canvas"]
        )

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
        self.invalidate_cache()
        self._selected_item = None
        self.queue_draw()

    def set_page(self, page_num):
        if not self._document:
            return
        self._page_num = max(0, min(page_num, self._document.page_count - 1))
        self._scroll_x = 0.0
        if self._continuous and self._page_offsets:
            self._scroll_y = self._page_offsets[self._page_num][1]
        else:
            self._scroll_y = 0.0
        self.invalidate_cache()
        self._selected_item = None
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

    def _get_page_pixbuf(self, page_num):
        key = (page_num, self._scale)
        if key not in self._page_cache:
            if len(self._page_cache) >= MAX_CACHE_SIZE:
                self._page_cache.pop(next(iter(self._page_cache)))
            png_data, w, h = self._document.render_page(page_num, self._scale)
            stream = GdkPixbuf.PixbufLoader.new_with_mime_type("image/png")
            stream.write(png_data)
            stream.close()
            self._page_cache[key] = stream.get_pixbuf()
        else:
            self._page_cache.move_to_end(key)
        return self._page_cache[key]

    def _rebuild_page_offsets(self):
        doc = self._document
        if not doc or not doc.is_loaded:
            self._page_offsets = []
            return
        offs = []
        y = 0
        for p in range(doc.page_count):
            pw, ph = doc.get_page_size(p)
            pw_disp = pw * self._scale
            ph_disp = ph * self._scale
            offs.append((p, y, pw_disp, ph_disp))
            y += ph_disp + 20
        self._page_offsets = offs

    def _find_page_at_y(self, canvas_y, scale, scroll_y):
        doc_y = canvas_y + scroll_y
        for p, py, pw_disp, ph_disp in self._page_offsets:
            if py <= doc_y < py + ph_disp:
                return p, py
        if self._page_offsets:
            if doc_y < 0:
                return self._page_offsets[0][0], self._page_offsets[0][1]
            last = self._page_offsets[-1]
            return last[0], last[1]
        return 0, 0

    def _continuous_scroll_y(self, page_offset):
        return self._scroll_y - page_offset

    def invalidate_cache(self):
        self._pixbuf = None
        self._page_cache = OrderedDict()
        self._page_offsets = []

    def invalidate_page_cache(self, page_num=None):
        if page_num is not None:
            keys_to_remove = [k for k in self._page_cache if k[0] == page_num]
            for k in keys_to_remove:
                del self._page_cache[k]
        else:
            self._page_cache.clear()

    @property
    def selected_item(self):
        return self._selected_item

    @selected_item.setter
    def selected_item(self, value):
        self._selected_item = value

    def toggle_continuous(self):
        self._continuous = not self._continuous
        self.invalidate_cache()
        self._scroll_x = 0.0
        self._scroll_y = 0.0
        self._page_num = 0
        self._selected_item = None
        self.queue_draw()

    @property
    def draw_x(self):
        return self._scroll_x + self._center_x

    @property
    def draw_y(self):
        return self._scroll_y + self._center_y

    def _is_dark(self):
        return Adw.StyleManager.get_default().get_dark()

    def _draw_welcome(self, cr, w, h):
        dark = self._is_dark()
        cx = w / 2
        top = 40

        title_color = (0.9, 0.9, 0.9) if dark else (0.2, 0.2, 0.2)
        sub_color = (0.55, 0.55, 0.55) if dark else (0.4, 0.4, 0.4)
        header_color = (0.8, 0.8, 0.8) if dark else (0.2, 0.2, 0.2)
        label_color = (0.5, 0.5, 0.5) if dark else (0.35, 0.35, 0.35)
        key_color = (0.7, 0.7, 0.7) if dark else (0.25, 0.25, 0.25)
        desc_color = (0.45, 0.45, 0.45) if dark else (0.45, 0.45, 0.45)
        footer_color = (0.35, 0.35, 0.35) if dark else (0.55, 0.55, 0.55)

        cr.set_source_rgb(*title_color)
        cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
        cr.set_font_size(24)
        label = "Chisel"
        te = cr.text_extents(label)
        cr.move_to(cx - te.width / 2, top + te.height)
        cr.show_text(label)

        cr.set_source_rgb(*sub_color)
        cr.select_font_face("Sans", cairo.FontSlant.ITALIC, cairo.FontWeight.NORMAL)
        cr.set_font_size(12)
        label = "The interactive PDF editor"
        te = cr.text_extents(label)
        cr.move_to(cx - te.width / 2, top + 24 + te.height)
        cr.show_text(label)

        left_x = 40
        right_x = cx + 20
        section_top = top + 70

        cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)

        cr.set_source_rgb(*header_color)
        cr.set_font_size(13)
        label = "Keyboard Shortcuts"
        cr.move_to(left_x, section_top)
        cr.show_text(label)

        label = "Tools"
        cr.move_to(right_x, section_top)
        cr.show_text(label)

        cr.set_source_rgb(*label_color)
        cr.set_font_size(10)

        row_h = 18
        for i, (key, desc) in enumerate(_SHORTCUTS):
            y = section_top + 20 + i * row_h
            cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
            cr.set_source_rgb(*key_color)
            cr.move_to(left_x + 10, y + 10)
            cr.show_text(key)
            cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)
            cr.set_source_rgb(*desc_color)
            cr.move_to(left_x + 130, y + 10)
            cr.show_text(desc)

        for i, (name, desc) in enumerate(_TOOLS):
            y = section_top + 20 + i * row_h
            cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
            cr.set_source_rgb(*key_color)
            cr.move_to(right_x + 10, y + 10)
            cr.show_text(name)
            cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)
            cr.set_source_rgb(*desc_color)
            cr.move_to(right_x + 65, y + 10)
            cr.show_text(desc)

        cr.set_source_rgb(*footer_color)
        cr.set_font_size(11)
        label = "Open a PDF to get started  (Ctrl+O)"
        te = cr.text_extents(label)
        cr.move_to(cx - te.width / 2, h - 30)
        cr.show_text(label)

    def _on_draw(self, area, cr, w, h):
        if self._is_dark():
            cr.set_source_rgb(0.15, 0.15, 0.15)
        else:
            cr.set_source_rgb(0.85, 0.85, 0.85)
        cr.paint()

        if not self._document or not self._document.is_loaded:
            self._draw_welcome(cr, w, h)
            return

        if self._continuous:
            self._draw_continuous(cr, w, h)
            return

        pixbuf = self._get_pixbuf()
        if pixbuf is None:
            return

        disp_w = pixbuf.get_width()
        disp_h = pixbuf.get_height()

        self._last_draw_size = (w, h)

        self._center_x = max(0, (w - disp_w) / 2)
        self._center_y = max(0, (h - disp_h) / 2)

        draw_x = self._scroll_x + self._center_x
        draw_y = self._scroll_y + self._center_y

        cr.translate(draw_x, draw_y)

        if self._is_dark():
            cr.set_source_rgb(0.2, 0.2, 0.2)
        else:
            cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, disp_w, disp_h)
        cr.fill()

        Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
        cr.paint()

        cr.translate(-draw_x, -draw_y)

        if self._active_tool:
            self._active_tool.draw_overlay(
                cr, w, h, self._scale, draw_x, draw_y
            )

    def _draw_continuous(self, cr, w, h):
        self._last_draw_size = (w, h)

        self._rebuild_page_offsets()
        if not self._page_offsets:
            return

        gap = 20
        last = self._page_offsets[-1]
        total_h = last[1] + last[3]

        max_scroll = max(0, total_h - h)
        self._scroll_y = max(0, min(self._scroll_y, max_scroll))

        # Update current page from viewport center
        center_y = self._scroll_y + h / 2
        old_page = self._page_num
        for p, py, _, ph_disp in self._page_offsets:
            if py <= center_y < py + ph_disp:
                self._page_num = p
                break
        if self._page_num != old_page:
            self.emit("page-changed", self._page_num)

        viewport_top = self._scroll_y - last[3]
        viewport_bot = self._scroll_y + h + last[3]

        for p, py, pw_disp, ph_disp in self._page_offsets:
            if py + ph_disp < viewport_top or py > viewport_bot:
                continue

            pixbuf = self._get_page_pixbuf(p)
            if pixbuf is None:
                continue

            center_x = max(0, (w - pw_disp) / 2)
            draw_x = self._scroll_x + center_x
            draw_y = py - self._scroll_y

            cr.save()
            cr.translate(draw_x, draw_y)
            if self._is_dark():
                cr.set_source_rgb(0.2, 0.2, 0.2)
            else:
                cr.set_source_rgb(1, 1, 1)
            cr.rectangle(0, 0, pw_disp, ph_disp)
            cr.fill()
            Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
            cr.paint()
            cr.restore()

        if self._active_tool and self._page_offsets:
            p, poff, pw_disp, _ = self._page_offsets[self._page_num]
            local_y = self._continuous_scroll_y(poff)
            draw_x = self._scroll_x + max(0, (w - pw_disp) / 2)
            draw_y = poff - self._scroll_y
            self._active_tool.draw_overlay(
                cr, w, h, self._scale, draw_x, draw_y
            )

    def _tool_scroll_for_pos(self, x, y):
        if not self._continuous or not self._page_offsets:
            return self.draw_x, self.draw_y
        p, poff = self._find_page_at_y(y, 1.0, self._scroll_y)
        self._page_num = p
        alloc = self.get_allocation()
        w = alloc.width
        pw_disp = self._page_offsets[p][2] if p < len(self._page_offsets) else 0
        center_x = max(0, (w - pw_disp) / 2)
        sx = self._scroll_x + center_x
        sy = poff - self._scroll_y
        return sx, sy

    def _on_click_pressed(self, gesture, n_press, x, y):
        self._press_pos = (x, y)
        self._drag_start_scroll = (self._scroll_x, self._scroll_y)
        self._is_pressed = True
        self._has_moved = False
        self._ctrl_held = bool(gesture.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK)
        if self._ctrl_held or self._active_tool is None:
            self._tool_is_dragging = False
        else:
            sx, sy = self._tool_scroll_for_pos(x, y)
            self._tool_is_dragging = self._active_tool.on_drag_begin(
                x, y, self._scale, sx, sy
            )

    def _on_motion(self, controller, x, y):
        if self._active_tool:
            sx, sy = self._tool_scroll_for_pos(x, y)
            self._active_tool.on_motion(x, y, self._scale, sx, sy)
        if not self._is_pressed:
            return
        dx = x - self._press_pos[0]
        dy = y - self._press_pos[1]
        if dx * dx + dy * dy < CLICK_THRESHOLD * CLICK_THRESHOLD:
            return
        self._has_moved = True
        if self._tool_is_dragging and self._active_tool:
            sx, sy = self._tool_scroll_for_pos(x, y)
            self._active_tool.on_drag_update(
                x, y, self._scale, sx, sy
            )
        elif self._ctrl_held or self._active_tool is None:
            self._scroll_x = self._drag_start_scroll[0] + dx
            self._scroll_y = self._drag_start_scroll[1] + dy
            self._clamp_scroll()
            self.queue_draw()

    def _on_click_released(self, gesture, n_press, x, y):
        if not self._is_pressed:
            return
        dx = x - self._press_pos[0]
        dy = y - self._press_pos[1]
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < CLICK_THRESHOLD and self._active_tool:
            sx, sy = self._tool_scroll_for_pos(x, y)
            self._active_tool.on_click(
                self._press_pos[0], self._press_pos[1],
                self._scale, sx, sy
            )
        elif self._has_moved and self._tool_is_dragging and self._active_tool:
            sx, sy = self._tool_scroll_for_pos(x, y)
            self._active_tool.on_drag_end(
                x, y, self._scale, sx, sy
            )
        self.grab_focus()
        self._is_pressed = False
        self._has_moved = False
        self._ctrl_held = False
        self._press_pos = None
        self._drag_start_scroll = None
        self._tool_is_dragging = False

    def _clamp_scroll(self):
        if self._continuous or not self._document or not self._document.is_loaded:
            return
        pw, ph = self._document.get_page_size(self._page_num)
        ph_disp = ph * self._scale
        alloc = self.get_allocation()
        max_scroll_y = max(0, ph_disp - alloc.height)
        self._scroll_y = min(0, max(-max_scroll_y, self._scroll_y))

    def _on_scroll(self, controller, dx, dy):
        if not self._document:
            return False
        state = controller.get_current_event_state()
        if state & Gdk.ModifierType.CONTROL_MASK:
            self._scale *= 1.1 if dy < 0 else 0.9
            self._scale = max(0.1, min(10.0, self._scale))
            self.invalidate_cache()
            self.queue_draw()
        elif self._continuous:
            self._scroll_y += dy * SCROLL_SPEED
        else:
            self._scroll_y -= dy * SCROLL_SPEED
        self._clamp_scroll()
        self.queue_draw()
        return True

    def _on_key_pressed(self, controller, keyval, keycode, state):
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        shift = state & Gdk.ModifierType.SHIFT_MASK
        if ctrl and keyval == Gdk.KEY_c:
            if self._active_tool:
                self._active_tool.on_copy()
            return True
        if ctrl and keyval == Gdk.KEY_v:
            if self._active_tool:
                self._active_tool.on_paste()
            return True
        if ctrl and keyval == Gdk.KEY_z:
            if self._document and self._document.is_loaded:
                self._document.journal_undo()
                self.invalidate_cache()
                self.queue_draw()
            return True
        if ctrl and shift and keyval == Gdk.KEY_Z:
            if self._document and self._document.is_loaded:
                self._document.journal_redo()
                self.invalidate_cache()
                self.queue_draw()
            return True
        if ctrl and keyval == Gdk.KEY_y:
            if self._document and self._document.is_loaded:
                self._document.journal_redo()
                self.invalidate_cache()
                self.queue_draw()
            return True
        if keyval == Gdk.KEY_Escape and self._active_tool:
            if self._active_tool.on_escape():
                self.queue_draw()
            return True
        if keyval in (Gdk.KEY_Delete, Gdk.KEY_BackSpace):
            if self._active_tool and self._active_tool.on_delete():
                return True
            if self._selected_item:
                self._document.start_op("delete selected")
                try:
                    page = self._document.doc[self._page_num]
                    if self._selected_item["type"] == "annot":
                        page.delete_annot(self._selected_item["annot"])
                    elif self._selected_item["type"] == "text":
                        span = self._selected_item["span"]
                        annot = page.add_redact_annot(span.bbox)
                        annot.set_colors(fill=(1, 1, 1))
                        page.apply_redactions()
                        page.clean_contents()
                finally:
                    self._document.stop_op()
                self._selected_item = None
                self.invalidate_cache()
                self.queue_draw()
                return True

        if not self._document:
            return False
        if keyval == Gdk.KEY_plus or keyval == Gdk.KEY_equal:
            self._scale *= 1.2
            self._scale = min(10.0, self._scale)
            self.invalidate_cache()
            self.queue_draw()
            return True
        elif keyval == Gdk.KEY_minus:
            self._scale *= 0.8
            self._scale = max(0.1, self._scale)
            self.invalidate_cache()
            self.queue_draw()
            return True
        elif keyval == Gdk.KEY_Page_Down:
            if self._continuous and self._page_offsets:
                next_page = min(self._page_num + 1, len(self._page_offsets) - 1)
                self._scroll_y = self._page_offsets[next_page][1]
                self.invalidate_cache()
            else:
                self.set_page(self._page_num + 1)
            return True
        elif keyval == Gdk.KEY_Page_Up:
            if self._continuous and self._page_offsets:
                prev_page = max(self._page_num - 1, 0)
                self._scroll_y = self._page_offsets[prev_page][1]
                self.invalidate_cache()
            else:
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
