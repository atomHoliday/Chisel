import sys
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from window import ChiselWindow


class ChiselApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.uncapyeti.chisel",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )

    def do_activate(self):
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.DEFAULT
        )
        win = self.get_active_window()
        if not win:
            win = ChiselWindow(application=self)
        win.present()

    def do_open(self, files, n_files, hint):
        win = self.get_active_window()
        if not win:
            win = ChiselWindow(application=self)
        win.present()
        if files:
            win.open_file(files[0].get_path())


def main():
    app = ChiselApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
