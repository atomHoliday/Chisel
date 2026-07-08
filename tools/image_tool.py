from gi.repository import Gtk, Gdk, Gio, GLib

from tools.base import Tool
from document.image_handler import (
    insert_image_file,
    insert_image_bytes,
    supported_image_extensions,
    get_image_natural_size,
)
from drawing.theme import IMAGE_FILL, IMAGE_BORDER, IMAGE_WIDTH


class ImageTool(Tool):
    name = "image"

    def __init__(self, canvas, document, window):
        super().__init__(canvas, document)
        self._window = window
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

    def on_click(self, x, y, scale, scroll_x, scroll_y):
        page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        self._pick_image(page_x, page_y)
        return True

    def on_drag_begin(self, x, y, scale, scroll_x, scroll_y):
        page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        self._drag_start = (page_x, page_y)
        self._is_dragging = True
        return True

    def on_drag_update(self, x, y, scale, scroll_x, scroll_y):
        if self._is_dragging and self._drag_start:
            page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
            self._drag_end = (page_x, page_y)
            self._canvas.queue_draw()
            return True
        return False

    def on_drag_end(self, x, y, scale, scroll_x, scroll_y):
        if self._is_dragging and self._drag_start and self._drag_end:
            sx, sy = self._drag_start
            ex, ey = self._drag_end
            rect = (
                min(sx, ex), min(sy, ey),
                max(sx, ex), max(sy, ey),
            )
            self._drag_start = None
            self._drag_end = None
            self._is_dragging = False
            self._canvas.queue_draw()
            self._pick_image_with_rect(rect)
            return True
        self._drag_start = None
        self._drag_end = None
        self._is_dragging = False
        return False

    def _pick_image(self, page_x, page_y):
        doc = self._document
        if not doc or not doc.is_loaded:
            return

        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Image")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filter = Gtk.FileFilter()
        exts = supported_image_extensions()
        filter.set_name("Images (" + ", ".join(exts) + ")")
        pattern_str = " ".join("*" + e for e in exts)
        for ext in exts:
            filter.add_pattern("*" + ext)
        filters.append(filter)
        dialog.set_filters(filters)

        dialog.open(self._window, None, lambda d, r: self._on_image_picked(
            d, r, page_x, page_y, None
        ), None)

    def _pick_image_with_rect(self, rect):
        doc = self._document
        if not doc or not doc.is_loaded:
            return

        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Image")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filter = Gtk.FileFilter()
        exts = supported_image_extensions()
        filter.set_name("Images (" + ", ".join(exts) + ")")
        for ext in exts:
            filter.add_pattern("*" + ext)
        filters.append(filter)
        dialog.set_filters(filters)

        dialog.open(self._window, None, lambda d, r: self._on_image_picked(
            d, r, None, None, rect
        ), None)

    def _on_image_picked(self, dialog, result, page_x, page_y, rect):
        try:
            file = dialog.open_finish(result)
            if file is None:
                return
            path = file.get_path()
            doc = self._document
            if not doc or not doc.is_loaded:
                return
            page_num = self._canvas.page_num

            if rect:
                insert_image_file(doc, page_num, rect, path)
            elif page_x is not None:
                natural = get_image_natural_size(path)
                if natural:
                    pw, ph = doc.get_page_size(page_num)
                    img_w = min(natural[0] / 10, pw * 0.5)
                    img_h = natural[1] * (img_w / natural[0])
                    img_rect = (page_x, page_y, page_x + img_w, page_y + img_h)
                    insert_image_file(doc, page_num, img_rect, path)

            self._canvas.invalidate_cache()
            self._canvas.invalidate_page_cache(self._canvas.page_num)
            self._canvas.queue_draw()
        except GLib.Error as e:
            if "dismissed" not in str(e).lower():
                print(f"Error picking image: {e}")

    def on_paste(self):
        if not self._document or not self._document.is_loaded:
            return False
        page_num = self._canvas.page_num
        alloc = self._canvas.get_allocation()
        if alloc.width > 0 and alloc.height > 0:
            cx = alloc.width / 2
            cy = alloc.height / 2
        else:
            cx, cy = 200, 200
        target_x, target_y = self.canvas_to_page(
            cx, cy, self._canvas.scale, self._canvas.draw_x, self._canvas.draw_y
        )
        clipboard = self._window.get_clipboard()
        clipboard.read_texture_async(
            None,
            self._on_clipboard_texture,
            (page_num, target_x, target_y),
        )
        return True

    def _on_clipboard_texture(self, clipboard, result, pos_data):
        try:
            texture = clipboard.read_texture_finish(result)
            if texture is None:
                return
            png_bytes = texture.save_to_png_bytes()
            image_data = png_bytes.get_data()
            doc = self._document
            if not doc or not doc.doc:
                return
            page_num, px, py = pos_data
            pw, ph = doc.get_page_size(page_num)
            tw, th = texture.get_width(), texture.get_height()
            img_w = min(tw / 10, pw * 0.5)
            img_h = th * (img_w / tw) if tw > 0 else img_w
            rect = (px, py, px + img_w, py + img_h)
            insert_image_bytes(doc, page_num, rect, image_data)
            self._canvas.invalidate_cache()
            self._canvas.invalidate_page_cache(self._canvas.page_num)
            self._canvas.queue_draw()
        except Exception:
            import traceback
            traceback.print_exc()

    def draw_overlay(self, cr, width, height, scale, scroll_x, scroll_y):
        if self._is_dragging and self._drag_start and self._drag_end:
            sx, sy = self._drag_start
            ex, ey = self._drag_end
            x = min(sx, ex) * scale + scroll_x
            y = min(sy, ey) * scale + scroll_y
            w = abs(ex - sx) * scale
            h = abs(ey - sy) * scale

            cr.save()
            cr.set_source_rgba(*IMAGE_FILL)
            cr.rectangle(x, y, w, h)
            cr.fill()
            cr.set_source_rgba(*IMAGE_BORDER)
            cr.set_line_width(IMAGE_WIDTH)
            cr.set_dash([4, 4], 0)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            cr.set_dash([], 0)
            cr.restore()
