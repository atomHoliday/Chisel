import pymupdf


class TextSpan:
    def __init__(self, page_num, bbox, text, font_size, font_name, origin, color=0):
        self.page_num = page_num
        self.bbox = bbox
        self.text = text
        self.font_size = font_size
        self.font_name = font_name
        self.origin = origin
        self.color = color

    def __repr__(self):
        return f"TextSpan({self.text!r}, bbox={self.bbox})"


def get_page_spans(doc, page_num):
    if doc._doc is None:
        return []
    page = doc._doc[page_num]
    blocks = page.get_text("dict")["blocks"]
    spans = []
    for block in blocks:
        if block["type"] != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                bbox = span["bbox"]
                spans.append(TextSpan(
                    page_num=page_num,
                    bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
                    text=span["text"],
                    font_size=span["size"],
                    font_name=span["font"],
                    origin=span["origin"],
                    color=span["color"],
                ))
    return spans


def find_span_at(doc, page_num, x, y):
    spans = get_page_spans(doc, page_num)
    for span in spans:
        bx0, by0, bx1, by1 = span.bbox
        if bx0 <= x <= bx1 and by0 <= y <= by1:
            return span
    return None


def get_page_chars(doc, page_num):
    if doc._doc is None:
        return []
    page = doc._doc[page_num]
    blocks = page.get_text("rawdict")["blocks"]
    chars = []
    for block in blocks:
        if block["type"] != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font_size = span.get("size", 10)
                font_name = span.get("font", "helv")
                for ch in span.get("chars", []):
                    b = ch["bbox"]
                    chars.append(TextSpan(
                        page_num=page_num,
                        bbox=(b[0], b[1], b[2], b[3]),
                        text=ch["c"],
                        font_size=font_size,
                        font_name=font_name,
                        origin=(b[0], b[3]),
                        color=span.get("color", 0),
                    ))
    return chars
