import pymupdf


class PdfDocument:
    def __init__(self):
        self._doc: pymupdf.Document | None = None
        self._path: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._doc is not None

    @property
    def path(self) -> str | None:
        return self._path

    @property
    def page_count(self) -> int:
        return len(self._doc) if self._doc else 0

    def load(self, path: str) -> None:
        self.close()
        self._doc = pymupdf.open(path)
        self._path = path

    def close(self) -> None:
        if self._doc:
            self._doc.close()
            self._doc = None
            self._path = None

    def get_page_size(self, page_num: int) -> tuple[float, float]:
        page = self._doc[page_num]
        rect = page.rect
        return rect.width, rect.height

    def render_page(self, page_num: int, scale: float = 1.0) -> tuple[bytes, int, int]:
        page = self._doc[page_num]
        matrix = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix)
        return pix.tobytes("png"), pix.width, pix.height

    def get_page_text(self, page_num: int) -> str:
        page = self._doc[page_num]
        return page.get_text("text")

    def save(self, path=None):
        if self._doc is None:
            return
        save_path = path or self._path
        if save_path:
            use_incremental = save_path == self._path
            self._doc.save(save_path, incremental=use_incremental, deflate=True)

    def save_as(self, path):
        if self._doc is None:
            return
        self._doc.save(path, deflate=True)
