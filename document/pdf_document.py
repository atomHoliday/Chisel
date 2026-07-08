import pymupdf


class PdfDocument:
    def __init__(self):
        self._doc: pymupdf.Document | None = None
        self._path: str | None = None

    @property
    def doc(self):
        return self._doc

    @property
    def is_loaded(self) -> bool:
        return self._doc is not None

    @property
    def path(self) -> str | None:
        return self._path

    @property
    def page_count(self) -> int:
        return len(self._doc) if self._doc else 0

    def _preload_fonts(self):
        if not self._doc or self._doc.page_count == 0:
            return
        for page in list(self._doc):
            for fname in ["Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
                          "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
                          "Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique"]:
                try:
                    page.insert_text((-100, -100), ".", fontname=fname, fontsize=1)
                except Exception:
                    pass

    def load(self, path: str) -> None:
        self.close()
        self._doc = pymupdf.open(path)
        self._path = path
        self._preload_fonts()
        self._doc.journal_enable()

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
            self._doc.save(save_path, deflate=True)

    def save_as(self, path):
        if self._doc is None:
            return
        self._doc.save(path, deflate=True)

    def start_op(self, name):
        if self._doc:
            self._doc.journal_start_op(name)

    def stop_op(self):
        if self._doc:
            self._doc.journal_stop_op()

    def journal_undo(self):
        if self._doc and self._doc.journal_can_do().get("undo"):
            self._doc.journal_undo()

    def journal_redo(self):
        if self._doc and self._doc.journal_can_do().get("redo"):
            self._doc.journal_redo()
