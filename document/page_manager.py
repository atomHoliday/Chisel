import pymupdf


class PageManager:
    def __init__(self, document):
        self._doc = document

    @property
    def document(self):
        return self._doc

    def insert_page(self, index=None):
        doc = self._doc.doc
        if doc is None:
            return
        if index is None or index > len(doc):
            index = len(doc)
        doc.new_page(index)

    def delete_page(self, index):
        doc = self._doc.doc
        if doc is None or not 0 <= index < len(doc) or len(doc) <= 1:
            return
        doc.delete_page(index)

    def move_page(self, from_idx, to_idx):
        doc = self._doc.doc
        if doc is None:
            return
        n = len(doc)
        if not (0 <= from_idx < n and 0 <= to_idx < n) or from_idx == to_idx:
            return
        doc.move_page(from_idx, to_idx)

    def duplicate_page(self, index):
        doc = self._doc.doc
        if doc is None or not 0 <= index < len(doc):
            return
        src = doc[index]
        new_page = doc.new_page(index + 1, width=src.rect.width, height=src.rect.height)
        new_page.show_pdf_page(src.rect, doc, index)

    def render_thumbnail(self, page_num, max_size=120):
        doc = self._doc.doc
        if doc is None or not 0 <= page_num < len(doc):
            return None
        page = doc[page_num]
        rect = page.rect
        scale = min(max_size / rect.width, max_size / rect.height)
        matrix = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix)
        return pix.tobytes("png"), pix.width, pix.height, page_num + 1
