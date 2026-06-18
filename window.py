import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Adw, Gio, GLib, GdkPixbuf, GObject
from gi.repository import Gdk

from canvas import PdfCanvas
from document.pdf_document import PdfDocument
from document.page_manager import PageManager
from document.flatten import flatten_annotations
from tools.select_tool import SelectTool
from tools.text_edit_tool import TextEditTool
from tools.fraction_edit_tool import FractionEditTool
from tools.image_tool import ImageTool
from tools.highlight_tool import HighlightTool
from tools.line_tool import LineTool
from tools.shape_tool import ShapeTool
from tools.callout_tool import CalloutTool
from tools.cut_tool import CutTool


class ToolProperties(GObject.Object):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self._props = {
            "stroke_color": (0, 0, 0),
            "stroke_width": 2,
            "fill_color": None,
            "has_arrow": False,
            "shape_type": "rectangle",
            "callout_text": "",
        }

    def get(self, key, default=None):
        return self._props.get(key, default)

    def set(self, key, value):
        self._props[key] = value
        self.emit("changed")

    def toggle(self, key):
        self._props[key] = not self._props.get(key, False)
        self.emit("changed")


class PropertiesPanel(Gtk.Popover):
    def __init__(self, props, parent_widget):
        super().__init__()
        self._props = props
        self.set_parent(parent_widget)
        self.set_position(Gtk.PositionType.BOTTOM)

        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)
        grid.set_margin_start(8)
        grid.set_margin_end(8)

        row = 0
        grid.attach(Gtk.Label(label="Stroke:"), 0, row, 1, 1)
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        for name, rgb in [("Black", (0, 0, 0)), ("Red", (0.8, 0, 0)),
                          ("Blue", (0, 0, 0.8)), ("Green", (0, 0.6, 0))]:
            btn = Gtk.ToggleButton()
            area = Gtk.DrawingArea()
            area.set_size_request(20, 20)
            area.set_draw_func(lambda a, cr, w, h, c=rgb: (
                cr.set_source_rgb(*c), cr.rectangle(2, 2, w-4, h-4), cr.fill()
            ))
            btn.set_child(area)
            btn.connect("toggled", self._on_color, name, rgb)
            if rgb == (0, 0, 0):
                btn.set_active(True)
            color_box.append(btn)
        grid.attach(color_box, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label="Width:"), 0, row, 1, 1)
        width_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        for val in [1, 2, 4, 6]:
            btn = Gtk.ToggleButton(label=str(val))
            btn.connect("toggled", self._on_width, val)
            if val == 2:
                btn.set_active(True)
            width_box.append(btn)
        grid.attach(width_box, 1, row, 1, 1)
        row += 1

        self._fill_btn = Gtk.CheckButton(label="Fill")
        self._fill_btn.connect("toggled", self._on_fill)
        grid.attach(self._fill_btn, 0, row, 2, 1)
        row += 1

        self._arrow_btn = Gtk.CheckButton(label="Arrow")
        self._arrow_btn.connect("toggled", self._on_arrow)
        grid.attach(self._arrow_btn, 0, row, 2, 1)
        row += 1

        grid.attach(Gtk.Label(label="Shape:"), 0, row, 1, 1)
        shape_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        for name in ["rectangle", "circle"]:
            btn = Gtk.ToggleButton(label=name.capitalize())
            btn.connect("toggled", self._on_shape, name)
            if name == "rectangle":
                btn.set_active(True)
            shape_box.append(btn)
        grid.attach(shape_box, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label="Callout text:"), 0, row, 1, 1)
        text_entry = Gtk.Entry()
        text_entry.set_placeholder_text("Type here...")
        text_entry.connect("changed", lambda e: props.set("callout_text", e.get_text()))
        grid.attach(text_entry, 1, row, 1, 1)

        self.set_child(grid)

    def _on_color(self, btn, name, rgb):
        if btn.get_active():
            self._props.set("stroke_color", rgb)

    def _on_width(self, btn, val):
        if btn.get_active():
            self._props.set("stroke_width", val)

    def _on_fill(self, btn):
        if btn.get_active():
            self._props.set("fill_color", (1, 1, 0, 0.3))
        else:
            self._props.set("fill_color", None)

    def _on_arrow(self, btn):
        self._props.set("has_arrow", btn.get_active())

    def _on_shape(self, btn, name):
        if btn.get_active():
            self._props.set("shape_type", name)


class PageThumbnailRow(Gtk.ListBoxRow):
    def __init__(self, page_num, thumbnail_data, thumb_w, thumb_h, label_text):
        super().__init__()
        self.page_num = page_num

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(4)
        box.set_margin_end(4)

        stream = GdkPixbuf.PixbufLoader.new_with_mime_type("image/png")
        stream.write(thumbnail_data)
        stream.close()
        pixbuf = stream.get_pixbuf()

        picture = Gtk.Picture.new_for_pixbuf(pixbuf)
        picture.set_size_request(thumb_w, thumb_h)
        box.append(picture)

        label = Gtk.Label(label=label_text)
        label.set_halign(Gtk.Align.CENTER)
        box.append(label)

        self.set_child(box)


class PageSidebar(Gtk.Box):
    __gsignals__ = {
        "page-selected": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self, page_manager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._pm = page_manager
        self._rows = []

        self.set_size_request(160, -1)
        self.set_vexpand(True)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.connect("row-activated", self._on_row_activated)
        self._listbox.connect("row-selected", self._on_row_selected)
        scrolled.set_child(self._listbox)

        self.append(scrolled)
        self._setup_context_menu()

    def _setup_context_menu(self):
        click = Gtk.GestureClick.new()
        click.set_button(3)
        click.connect("pressed", self._on_context_menu)
        self._listbox.add_controller(click)

    def _on_context_menu(self, gesture, n_press, x, y):
        row = self._listbox.get_row_at_y(y)
        if row is None:
            return
        self._listbox.select_row(row)

        builder = Gtk.Builder()
        menu_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="page-menu">
    <section>
      <item>
        <attribute name="label" translatable="yes">Insert Before</attribute>
        <attribute name="action">win.page-insert-before</attribute>
      </item>
      <item>
        <attribute name="label" translatable="yes">Insert After</attribute>
        <attribute name="action">win.page-insert-after</attribute>
      </item>
      <item>
        <attribute name="label" translatable="yes">Duplicate</attribute>
        <attribute name="action">win.page-duplicate</attribute>
      </item>
      <item>
        <attribute name="label" translatable="yes">Delete</attribute>
        <attribute name="action">win.page-delete</attribute>
      </item>
      <item>
        <attribute name="label" translatable="yes">Move Up</attribute>
        <attribute name="action">win.page-move-up</attribute>
      </item>
      <item>
        <attribute name="label" translatable="yes">Move Down</attribute>
        <attribute name="action">win.page-move-down</attribute>
      </item>
    </section>
  </menu>
</interface>'''
        builder.add_from_string(menu_xml)
        menu_widget = builder.get_object("page-menu")
        popover = Gtk.PopoverMenu.new_from_model(menu_widget)
        popover.set_parent(self._listbox)
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        popover.set_pointing_to(rect)
        popover.popup()

    def _on_row_activated(self, listbox, row):
        self.emit("page-selected", row.page_num)

    def _on_row_selected(self, listbox, row):
        if row:
            self.emit("page-selected", row.page_num)

    def rebuild(self):
        self._listbox.remove_all()
        self._rows.clear()
        doc = self._pm._doc
        if not doc._doc:
            return
        for i in range(doc.page_count):
            result = self._pm.render_thumbnail(i)
            if result is None:
                continue
            png_data, w, h, label = result
            row = PageThumbnailRow(i, png_data, w, h, str(label))
            self._listbox.append(row)
            self._rows.append(row)

    def select_page(self, page_num):
        if 0 <= page_num < len(self._rows):
            self._listbox.select_row(self._rows[page_num])


class ChiselWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._document = PdfDocument()
        self._canvas = PdfCanvas()
        self._page_manager = PageManager(self._document)
        self._props = ToolProperties()

        self._overlay = Gtk.Overlay()
        self._overlay.set_child(self._canvas)
        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(self._overlay)
        self._setup_tools()

        self.set_default_size(1024, 768)
        self.set_title("Chisel")
        self.connect("notify::fullscreened", self._on_fullscreen_changed)
        self.connect("notify::maximized", self._on_fullscreen_changed)

        headerbar = Adw.HeaderBar()

        file_button = Gtk.MenuButton()
        file_button.set_child(Gtk.Image.new_from_icon_name("open-menu-symbolic"))
        file_button.set_tooltip_text("File menu")
        file_menu_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="file-menu">
    <section>
      <item>
        <attribute name="label" translatable="yes">Open</attribute>
        <attribute name="action">win.open</attribute>
      </item>
      <item>
        <attribute name="label" translatable="yes">Save</attribute>
        <attribute name="action">win.save</attribute>
      </item>
      <item>
        <attribute name="label" translatable="yes">Save As...</attribute>
        <attribute name="action">win.save-as</attribute>
      </item>
    </section>
    <section>
      <item>
        <attribute name="label" translatable="yes">Flatten Annotations</attribute>
        <attribute name="action">win.flatten</attribute>
      </item>
    </section>
  </menu>
</interface>'''
        builder = Gtk.Builder()
        builder.add_from_string(file_menu_xml)
        file_menu = builder.get_object("file-menu")
        file_button.set_menu_model(file_menu)
        headerbar.pack_start(file_button)

        self._sidebar_button = Gtk.Button(icon_name="sidebar-show-symbolic")
        self._sidebar_button.set_tooltip_text("Toggle Page Sidebar")
        self._sidebar_button.connect("clicked", self._toggle_sidebar)
        headerbar.pack_start(self._sidebar_button)

        tool_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self._tool_buttons = []

        tools_config = [
            ("pan", "Pan", "Pan (default)", "selection-mode-symbolic"),
            ("select", "Sel", "Select text", "edit-select-symbolic"),
            ("text_edit", "Text", "Edit text", "insert-text-symbolic"),
            ("fraction", "Frac", "Fraction editor", None),
            ("image", "Img", "Insert image", "insert-image-symbolic"),
            ("highlight", "High", "Highlight", "text-highlight-symbolic"),
            ("line", "Line", "Line / Arrow", None),
            ("shape", "Shape", "Rectangle / Circle", "insert-object-symbolic"),
            ("callout", "Call", "Callout", "annotations-text-symbolic"),
            ("cut", "Cut", "Cut (redact)", "edit-cut-symbolic"),
        ]

        group = None
        for tool_id, label, tip, icon_name in tools_config:
            btn = Gtk.ToggleButton()
            btn.set_tooltip_text(tip)
            if icon_name:
                btn.set_child(Gtk.Image.new_from_icon_name(icon_name))
            else:
                btn.set_label(label)
            if group is not None:
                btn.set_group(group)
            else:
                group = btn
            btn.connect("toggled", self._on_tool_toggled, tool_id)
            tool_box.append(btn)
            self._tool_buttons.append(btn)

        self._tool_buttons[0].set_active(True)
        headerbar.pack_start(tool_box)

        self._props_btn = Gtk.Button()
        self._props_btn.set_child(Gtk.Image.new_from_icon_name("document-properties-symbolic"))
        self._props_btn.set_tooltip_text("Tool properties")
        self._props_panel = PropertiesPanel(self._props, self._props_btn)
        self._props_btn.connect("clicked", lambda b: self._props_panel.popup())
        headerbar.pack_start(self._props_btn)

        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        zoom_out = Gtk.Button.new_from_icon_name("zoom-out-symbolic")
        zoom_out.connect("clicked", lambda b: self._zoom(0.8))
        zoom_box.append(zoom_out)

        self._zoom_label = Gtk.Label(label="100%")
        zoom_box.append(self._zoom_label)

        zoom_in = Gtk.Button.new_from_icon_name("zoom-in-symbolic")
        zoom_in.connect("clicked", lambda b: self._zoom(1.2))
        zoom_box.append(zoom_in)

        zoom_fit = Gtk.Button.new_from_icon_name("zoom-fit-best-symbolic")
        zoom_fit.connect("clicked", lambda b: self._zoom_fit())
        zoom_box.append(zoom_fit)

        headerbar.set_title_widget(zoom_box)

        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        prev = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        prev.connect("clicked", lambda b: self._go_page(-1))
        nav_box.append(prev)

        self._page_label = Gtk.Label(label="0 / 0")
        nav_box.append(self._page_label)

        next = Gtk.Button.new_from_icon_name("go-next-symbolic")
        next.connect("clicked", lambda b: self._go_page(1))
        nav_box.append(next)

        headerbar.pack_end(nav_box)

        self._sidebar = PageSidebar(self._page_manager)
        self._sidebar.connect("page-selected", self._on_sidebar_page_selected)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_start_child(self._sidebar)
        paned.set_end_child(self._toast_overlay)
        paned.set_shrink_start_child(False)
        paned.set_resize_start_child(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(headerbar)
        box.append(paned)

        self.set_content(box)
        self._setup_actions()
        self._sidebar_visible = True

    def _setup_tools(self):
        self._tools = {
            "pan": None,
            "select": SelectTool(self._canvas, self._document),
            "text_edit": TextEditTool(self._canvas, self._document, self._overlay, self._toast_overlay),
            "fraction": FractionEditTool(self._canvas, self._document, self._overlay, self._toast_overlay),
            "image": ImageTool(self._canvas, self._document, self),
            "highlight": HighlightTool(self._canvas, self._document, self._props),
            "line": LineTool(self._canvas, self._document, self._props),
            "shape": ShapeTool(self._canvas, self._document, self._props),
            "callout": CalloutTool(self._canvas, self._document, self._props),
            "cut": CutTool(self._canvas, self._document),
        }

    def _on_tool_toggled(self, button, tool_id):
        if not button.get_active():
            return
        self._canvas.set_active_tool(self._tools.get(tool_id))

    def _toggle_sidebar(self, button):
        self._sidebar_visible = not self._sidebar_visible
        self._sidebar.set_visible(self._sidebar_visible)
        icon = "sidebar-show-symbolic" if self._sidebar_visible else "sidebar-hide-symbolic"
        self._sidebar_button.set_icon_name(icon)

    def _setup_actions(self):
        for name in ("open", "save", "save-as", "flatten"):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", getattr(self, f"_on_{name.replace('-', '_')}"))
            self.add_action(action)

        for name in ("zoom-in", "zoom-out", "zoom-fit"):
            action = Gio.SimpleAction.new(name, None)
            method = getattr(self, f"_on_{name.replace('-', '_')}")
            action.connect("activate", method)
            self.add_action(action)

        for name in ("page-insert-before", "page-insert-after",
                      "page-duplicate", "page-delete",
                      "page-move-up", "page-move-down"):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", getattr(self, f"_on_{name.replace('-', '_')}"))
            self.add_action(action)

        app = self.get_application()
        if app:
            accels = {
                "win.open": ["<Ctrl>o"],
                "win.save": ["<Ctrl>s"],
                "win.save-as": ["<Ctrl><Shift>s"],
                "win.zoom-in": ["<Ctrl>plus", "<Ctrl>equal"],
                "win.zoom-out": ["<Ctrl>minus"],
                "win.zoom-fit": ["<Ctrl>0"],
            }
            for action, keys in accels.items():
                app.set_accels_for_action(action, keys)

    def _on_open(self, action=None, param=None):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Open PDF")
        filter = Gtk.FileFilter()
        filter.set_name("PDF files")
        filter.add_pattern("*.pdf")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter)
        dialog.set_filters(filters)
        dialog.open(self, None, self._on_open_complete, None)

    def _on_open_complete(self, dialog, result, data):
        try:
            file = dialog.open_finish(result)
            if file:
                self.open_file(file.get_path())
        except GLib.Error as e:
            if "dismissed" not in str(e).lower():
                print(f"Error opening file: {e}")

    def _on_save(self, action, param):
        if not self._document.is_loaded:
            return
        if self._document.path:
            self._document.save()
        else:
            self._on_save_as(action, param)

    def _on_save_as(self, action, param):
        if not self._document.is_loaded:
            return
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Save PDF As")
        filter = Gtk.FileFilter()
        filter.set_name("PDF files")
        filter.add_pattern("*.pdf")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter)
        dialog.set_filters(filters)
        dialog.save(self, None, self._on_save_complete, None)

    def _on_save_complete(self, dialog, result, data):
        try:
            file = dialog.save_finish(result)
            if file:
                path = file.get_path()
                if not path.lower().endswith(".pdf"):
                    path += ".pdf"
                self._document.save_as(path)
                import os
                title = os.path.basename(path)
                self.set_title(f"{title} — Chisel")
        except GLib.Error as e:
            if "dismissed" not in str(e).lower():
                print(f"Error saving file: {e}")

    def _on_flatten(self, action, param):
        if not self._document.is_loaded:
            return
        flatten_annotations(self._document)
        self._canvas._pixbuf = None
        self._canvas.queue_draw()

    def open_file(self, path):
        self._document.load(path)
        self._canvas.set_document(self._document)
        self._sidebar.rebuild()
        import os
        title = os.path.basename(path)
        self.set_title(f"{title} — Chisel")
        self._update_page_label()

    def _on_zoom_in(self, action, param):
        self._zoom(1.2)

    def _on_zoom_out(self, action, param):
        self._zoom(0.8)

    def _on_zoom_fit(self, action, param):
        self._do_zoom_fit()

    def _zoom(self, factor):
        new_scale = self._canvas.scale * factor
        new_scale = max(0.1, min(10.0, new_scale))
        self._canvas._scale = new_scale
        self._canvas._pixbuf = None
        self._canvas.queue_draw()
        self._update_zoom_label()

    def _on_fullscreen_changed(self, window, pspec):
        if window.is_fullscreen() or window.is_maximized():
            GLib.idle_add(self._do_zoom_fit)

    def _do_zoom_fit(self):
        if not self._document.is_loaded:
            return
        alloc = self._canvas.get_allocation()
        w, h = self._document.get_page_size(self._canvas.page_num)
        if w > 0 and h > 0:
            scale_x = alloc.width / w if alloc.width > 0 else 1
            scale_y = alloc.height / h if alloc.height > 0 else 1
            self._canvas._scale = max(0.1, min(10.0, min(scale_x, scale_y) * 0.95))
            self._canvas._pixbuf = None
            self._canvas.queue_draw()
            self._update_zoom_label()

    def _go_page(self, delta):
        if not self._document.is_loaded:
            return
        new_page = self._canvas.page_num + delta
        self._canvas.set_page(new_page)
        self._sidebar.select_page(new_page)
        self._update_page_label()

    def _on_sidebar_page_selected(self, sidebar, page_num):
        self._canvas.set_page(page_num)
        self._update_page_label()

    def _update_page_label(self):
        total = self._document.page_count
        current = self._canvas.page_num + 1
        self._page_label.set_text(f"{current} / {total}")

    def _update_zoom_label(self):
        pct = int(self._canvas.scale * 100)
        self._zoom_label.set_text(f"{pct}%")

    def _current_page(self):
        return self._canvas.page_num

    def _on_page_insert_before(self, action, param):
        idx = self._current_page()
        self._page_manager.insert_page(idx)
        self._sidebar.rebuild()
        self._sidebar.select_page(idx)
        self._update_page_label()
        self._canvas.queue_draw()

    def _on_page_insert_after(self, action, param):
        idx = self._current_page() + 1
        self._page_manager.insert_page(idx)
        self._sidebar.rebuild()
        self._sidebar.select_page(idx)
        self._update_page_label()
        self._canvas.queue_draw()

    def _on_page_duplicate(self, action, param):
        idx = self._current_page()
        self._page_manager.duplicate_page(idx)
        self._sidebar.rebuild()
        self._sidebar.select_page(idx + 1)
        self._update_page_label()
        self._canvas.queue_draw()

    def _on_page_delete(self, action, param):
        idx = self._current_page()
        if self._document.page_count <= 1:
            return
        self._page_manager.delete_page(idx)
        new_idx = min(idx, self._document.page_count - 1)
        self._canvas.set_page(new_idx)
        self._sidebar.rebuild()
        self._sidebar.select_page(new_idx)
        self._update_page_label()
        self._canvas.queue_draw()

    def _on_page_move_up(self, action, param):
        idx = self._current_page()
        if idx <= 0:
            return
        self._page_manager.move_page(idx, idx - 1)
        self._canvas.set_page(idx - 1)
        self._sidebar.rebuild()
        self._sidebar.select_page(idx - 1)
        self._update_page_label()
        self._canvas.queue_draw()

    def _on_page_move_down(self, action, param):
        idx = self._current_page()
        if idx >= self._document.page_count - 1:
            return
        self._page_manager.move_page(idx, idx + 1)
        self._canvas.set_page(idx + 1)
        self._sidebar.rebuild()
        self._sidebar.select_page(idx + 1)
        self._update_page_label()
        self._canvas.queue_draw()
