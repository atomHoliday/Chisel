class Fraction:
    def __init__(self, page_num, bbox, numerator_text, denominator_text, line_rect,
                 font_size=None, font_name="helv", num_bbox=None, den_bbox=None,
                 num_origin=None, den_origin=None,
                 sep_bbox=None, sep_origin=None, sep_text=None):
        self.page_num = page_num
        self.bbox = bbox
        self.numerator_text = numerator_text
        self.denominator_text = denominator_text
        self.line_rect = line_rect
        self.font_size = font_size
        self.font_name = font_name
        self.num_bbox = num_bbox
        self.den_bbox = den_bbox
        self.num_origin = num_origin
        self.den_origin = den_origin
        self.sep_bbox = sep_bbox
        self.sep_origin = sep_origin
        self.sep_text = sep_text

    @property
    def display_text(self):
        sep = self.sep_text or "/"
        return f"{self.numerator_text}{sep}{self.denominator_text}"

    def __repr__(self):
        return f"Fraction({self.numerator_text}/{self.denominator_text} @ {self.bbox})"


def get_horizontal_lines(doc, page_num):
    if doc.doc is None:
        return []
    page = doc.doc[page_num]
    drawings = page.get_drawings()
    lines = []
    for d in drawings:
        rect = d["rect"]
        h = rect.y1 - rect.y0
        w = rect.x1 - rect.x0
        if h < 3 and w > 5:
            lines.append({
                "x0": rect.x0, "y0": rect.y0,
                "x1": rect.x1, "y1": rect.y1,
                "mid_y": (rect.y0 + rect.y1) / 2,
                "width": w,
            })
    return lines


def detect_fractions(doc, page_num):
    from document.text_model import get_page_spans
    spans = get_page_spans(doc, page_num)
    lines = get_horizontal_lines(doc, page_num)

    fractions = []

    used_spans = set()

    for line in lines:
        line_y = line["mid_y"]
        line_x0 = line["x0"]
        line_x1 = line["x1"]
        line_center = (line_x0 + line_x1) / 2

        above = None
        below = None

        for i, s in enumerate(spans):
            if i in used_spans:
                continue
            sx0, sy0, sx1, sy1 = s.bbox
            smid_x = (sx0 + sx1) / 2

            dist_from_line = abs(smid_x - line_center)
            span_width = sx1 - sx0
            if dist_from_line > max(span_width * 3, 30):
                continue

            overlap_x = max(0, min(sx1, line_x1) - max(sx0, line_x0))
            if overlap_x <= 0:
                continue

            gap_above = line_y - sy1
            gap_below = sy0 - line_y

            if 0 < gap_above < 20 and above is None:
                above = (i, s)
            elif 0 < gap_below < 20 and below is None:
                below = (i, s)

        if above and below:
            ai, a_span = above
            bi, b_span = below
            used_spans.add(ai)
            used_spans.add(bi)
            fx0 = min(a_span.bbox[0], b_span.bbox[0])
            fy0 = a_span.bbox[1]
            fx1 = max(a_span.bbox[2], b_span.bbox[2])
            fy1 = b_span.bbox[3]
            font_size = max(a_span.font_size, b_span.font_size)
            font_name = getattr(a_span, "font_name", "helv")
            fractions.append(Fraction(
                page_num=page_num,
                bbox=(fx0, fy0, fx1, fy1),
                numerator_text=a_span.text,
                denominator_text=b_span.text,
                line_rect=(line_x0, line_y, line_x1, line_y),
                font_size=font_size,
                font_name=font_name,
                num_bbox=a_span.bbox,
                den_bbox=b_span.bbox,
                num_origin=a_span.origin,
                den_origin=b_span.origin,
            ))

    remaining = [s for i, s in enumerate(spans) if i not in used_spans]
    more = _detect_fractions_without_lines(doc, page_num, lines)
    fractions.extend(more)

    return fractions


def _detect_fractions_without_lines(doc, page_num, lines):
    from document.text_model import get_page_chars
    chars = get_page_chars(doc, page_num)
    fractions = []
    n = len(chars)
    used = set()

    for i in range(n):
        if i in used:
            continue
        for j in range(i + 1, n):
            if j in used:
                continue
            a = chars[i]
            b = chars[j]
            ax0, ay0, ax1, ay1 = a.bbox
            bx0, by0, bx1, by1 = b.bbox

            if not (a.text.isdigit() and b.text.isdigit()):
                continue

            if max(a.font_size, b.font_size) > 5.5:
                continue

            overlap_x = min(ax1, bx1) - max(ax0, bx0)
            if overlap_x < -2:
                continue

            # If chars significantly overlap vertically, use list order (same line)
            # Otherwise use vertical position (higher on page = numerator)
            ch_a_h = ay1 - ay0
            ch_b_h = by1 - by0
            vh = min(ay1, by1) - max(ay0, by0)
            overlap_ratio = vh / max(1, min(ch_a_h, ch_b_h))

            if overlap_ratio > 0.3:
                num, den = a, b
            elif ay0 < by0:
                num, den = a, b
            else:
                num, den = b, a

            nx0, ny0, nx1, ny1 = num.bbox
            dx0, dy0, dx1, dy1 = den.bbox

            gap = dy0 - ny1
            if gap > 25 or gap < -5:
                continue

            size_ratio = max(num.font_size, den.font_size) / max(1, min(num.font_size, den.font_size))
            if size_ratio > 1.8:
                continue

            gap_center_y = (ny1 + dy0) / 2
            line_nearby = any(
                abs(l["mid_y"] - gap_center_y) < 15
                and min(l["x1"], nx1) - max(l["x0"], nx0) > 0
                for l in lines
            )

            if not line_nearby and gap > 12:
                continue

            used.add(i)
            used.add(j)
            fx0 = min(nx0, dx0)
            fy0 = ny0
            fx1 = max(nx1, dx1)
            fy1 = dy1
            font_size = max(num.font_size, den.font_size)
            font_name = getattr(num, "font_name", "helv")
            fractions.append(Fraction(
                page_num=page_num,
                bbox=(fx0, fy0, fx1, fy1),
                numerator_text=num.text,
                denominator_text=den.text,
                line_rect=None,
                font_size=font_size,
                font_name=font_name,
                num_bbox=num.bbox,
                den_bbox=den.bbox,
                num_origin=num.origin,
                den_origin=den.origin,
            ))
            break

    return fractions


def find_fraction_at(doc, page_num, x, y):
    fractions = detect_fractions(doc, page_num)
    for f in fractions:
        fx0, fy0, fx1, fy1 = f.bbox
        if fx0 <= x <= fx1 and fy0 <= y <= fy1:
            return f
    return None
