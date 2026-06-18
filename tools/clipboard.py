class Clipboard:
    def __init__(self):
        self._data = None

    def copy(self, data):
        self._data = data

    def paste(self):
        return self._data

    @property
    def has_data(self):
        return self._data is not None

    def clear(self):
        self._data = None


_clipboard = Clipboard()


def get_clipboard():
    return _clipboard
