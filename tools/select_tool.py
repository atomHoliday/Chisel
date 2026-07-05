import pymupdf
from tools.base import Tool
from tools.clipboard import get_clipboard
from document.text_model import find_span_at


class SelectTool(Tool):
    name = "select"

    def __init__(self, canvas, document):
        super().__init__(canvas, document)
        self._selected_span = None
        self._selected_annot = None
        self._page_num = -1
        self._pending_paste = None
        self._paste_pos = (0, 0)

    def activate(self):
        self._cancel_paste()
        self._canvas.queue_draw()

    def deactivate(self):
        self._cancel_paste()
        self._canvas.queue_draw()

    def _cancel_paste(self):
        self._pending_paste = None
        self._canvas.queue_draw()

    def on_motion(self, x, y, scale, scroll_x, scroll_y):
        if self._pending_paste:
            self._paste_pos = (x, y)
            self._canvas.queue_draw()
            return True
        return False

    def on_escape(self):
        if self._pending_paste:
            self._cancel_paste()
            return True
        self._selected_span = None
        self._selected_annot = None
        self._canvas._selected_item = None
        self._canvas.queue_draw()
        return True

    def on_click(self, x, y, scale, scroll_x, scroll_y):
        if self._pending_paste:
            page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
            self._commit_paste(page_x, page_y)
            return True

        page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        doc = self._document
        if not doc or not doc.is_loaded:
            return False
        page_num = self._canvas.page_num

        span = find_span_at(doc, page_num, page_x, page_y)
        if span:
            self._selected_span = span
            self._selected_annot = None
            self._page_num = page_num
            self._canvas._selected_item = {"type": "text", "span": span}
            self._canvas.queue_draw()
            return True

        annot = self._find_annot_at(doc, page_num, page_x, page_y)
        if annot:
            self._selected_annot = annot
            self._selected_span = None
            self._page_num = page_num
            self._canvas._selected_item = {"type": "annot", "annot": annot}
            self._canvas.queue_draw()
            return True

        self._selected_span = None
        self._selected_annot = None
        self._canvas._selected_item = None
        self._canvas.queue_draw()
        return True

    def on_drag_begin(self, x, y, scale, scroll_x, scroll_y):
        if self._pending_paste:
            return True
        return False

    def on_drag_end(self, x, y, scale, scroll_x, scroll_y):
        if self._pending_paste:
            page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
            self._commit_paste(page_x, page_y)
            return True
        return False

    def _commit_paste(self, page_x, page_y):
        data = self._pending_paste
        doc = self._document
        if not doc or not doc._doc:
            return
        page = doc._doc[self._canvas.page_num]
        self._pending_paste = None

        if data["type"] == "annot":
            doc._doc.journal_start_op("paste annot")
            try:
                r = data["rect"]
                ow = r[2] - r[0]
                oh = r[3] - r[1]
                rect = (page_x, page_y, page_x + ow, page_y + oh)
                atype = data["annot_type"]

                if atype == "Line":
                    p1 = (page_x, page_y)
                    p2 = (page_x + ow, page_y + oh)
                    new_annot = page.add_line_annot(p1, p2)
                    line_ends = data.get("line_ends")
                    if line_ends:
                        new_annot.set_line_ends(line_ends[0], line_ends[1])
                elif atype == "Square":
                    new_annot = page.add_rect_annot(rect)
                elif atype == "Circle":
                    new_annot = page.add_circle_annot(rect)
                elif atype == "FreeText":
                    content = data["info"].get("content", "")
                    new_annot = page.add_freetext_annot(
                        rect, content,
                        fontsize=10,
                        text_color=data["colors"]["stroke"],
                        border_width=data["border"]["width"],
                    )
                elif atype == "Highlight":
                    new_annot = page.add_highlight_annot(rect)
                else:
                    return

                colors = data["colors"]
                if colors["stroke"]:
                    new_annot.set_colors(stroke=tuple(colors["stroke"]))
                if colors["fill"]:
                    new_annot.set_colors(fill=tuple(colors["fill"]))
                bw = data["border"]["width"]
                if bw:
                    new_annot.set_border(width=bw)
                new_annot.update()
            finally:
                doc._doc.journal_stop_op()

            self._selected_annot = new_annot
            self._selected_span = None

        elif data["type"] == "text":
            from tools.fraction_edit_tool import _builtin_font
            text = data["text"]
            font_size = data.get("font_size", 10)
            font_name = data.get("font_name", "Helvetica")
            color_int = data.get("color", 0)
            color = (
                ((color_int >> 16) & 0xff) / 255,
                ((color_int >> 8) & 0xff) / 255,
                (color_int & 0xff) / 255,
            )
            fontname = _builtin_font(font_name)
            _, ph = doc.get_page_size(self._canvas.page_num)
            py = ph - page_y
            doc._doc.journal_start_op("paste text")
            try:
                page.insert_text((page_x, py), text, fontname=fontname, fontsize=font_size, color=color)
            finally:
                doc._doc.journal_stop_op()
            self._selected_annot = None
            self._selected_span = None

        self._page_num = self._canvas.page_num
        if data["type"] == "annot":
            self._canvas._selected_item = {"type": "annot", "annot": new_annot}
        else:
            self._canvas._selected_item = None
        self._canvas._pixbuf = None
        self._canvas.queue_draw()

    def _find_annot_at(self, doc, page_num, page_x, page_y):
        page = doc._doc[page_num]
        try:
            annot_iter = page.annots()
            annots = list(annot_iter) if annot_iter else []
        except Exception:
            return None
        for annot in reversed(annots):
            try:
                rect = annot.rect
            except Exception:
                continue
            if rect.x0 <= page_x <= rect.x1 and rect.y0 <= page_y <= rect.y1:
                return annot
        return None

    def delete_selected(self):
        if self._page_num != self._canvas.page_num:
            return False
        doc = self._document
        if not doc or not doc._doc:
            return False

        if self._selected_annot is not None:
            doc.start_op("delete selected")
            try:
                page = doc._doc[self._page_num]
                page.delete_annot(self._selected_annot)
            finally:
                doc.stop_op()
            self._selected_annot = None
            self._canvas._selected_item = None
            self._canvas._pixbuf = None
            self._canvas.queue_draw()
            return True

        if self._selected_span is not None:
            doc.start_op("delete selected")
            try:
                page = doc._doc[self._page_num]
                annot = page.add_redact_annot(self._selected_span.bbox)
                annot.set_colors(fill=(1, 1, 1))
                page.apply_redactions()
                page.clean_contents()
            finally:
                doc.stop_op()
            self._selected_span = None
            self._canvas._selected_item = None
            self._canvas._pixbuf = None
            self._canvas.queue_draw()
            return True

        return False

    def _serialize_annot(self, annot):
        colors = annot.colors
        border = annot.border
        info = annot.info
        rect = annot.rect
        data = {
            "type": "annot",
            "annot_type": annot.type[1],
            "rect": (rect.x0, rect.y0, rect.x1, rect.y1),
            "colors": {
                "stroke": colors.get("stroke", None) or None,
                "fill": colors.get("fill", None) or None,
            },
            "border": {
                "width": border.get("width", 0),
                "dashes": border.get("dashes", ()),
                "style": border.get("style", "S"),
            },
            "info": {
                "content": info.get("content", ""),
            },
        }
        if annot.type[1] == "Line":
            data["line_ends"] = annot.line_ends
        return data

    def on_copy(self):
        if self._selected_annot is not None:
            data = self._serialize_annot(self._selected_annot)
            get_clipboard().copy(data)
            return True
        if self._selected_span is not None:
            span = self._selected_span
            data = {
                "type": "text",
                "text": span.text,
                "font_size": span.font_size,
                "font_name": span.font_name,
                "origin": span.origin,
                "bbox": span.bbox,
                "color": span.color,
            }
            get_clipboard().copy(data)
            return True
        return False

    def on_paste(self):
        clip = get_clipboard()
        if not clip.has_data:
            return False
        data = clip.paste()
        self._pending_paste = data
        self._canvas.queue_draw()
        return True

    def draw_overlay(self, cr, width, height, scale, scroll_x, scroll_y):
        if self._pending_paste:
            x, y = self._paste_pos
            data = self._pending_paste
            if data["type"] == "annot":
                r = data["rect"]
                pw = (r[2] - r[0]) * scale
                ph = (r[3] - r[1]) * scale
            else:
                text = data["text"]
                fs = data.get("font_size", 10)
                pw = max(40, len(text) * fs * 0.65 + 16) * scale
                ph = max(20, fs * 1.5 + 16) * scale

            cr.save()
            cr.set_source_rgba(0.3, 0.6, 1.0, 0.35)
            cr.rectangle(x, y, pw, ph)
            cr.fill()
            cr.set_source_rgba(0.3, 0.6, 1.0, 0.8)
            cr.set_line_width(2)
            cr.rectangle(x, y, pw, ph)
            cr.stroke()
            cr.restore()
            return

        if self._page_num != self._canvas.page_num:
            return

        if self._canvas._selected_item is None:
            self._selected_annot = None
            self._selected_span = None

        if self._selected_annot is not None:
            r = self._selected_annot.rect
            x = r.x0 * scale + scroll_x
            y = r.y0 * scale + scroll_y
            w = (r.x1 - r.x0) * scale
            h = (r.y1 - r.y0) * scale
            cr.save()
            cr.set_source_rgba(0.3, 0.6, 1.0, 0.25)
            cr.rectangle(x, y, w, h)
            cr.fill()
            cr.set_source_rgba(0.3, 0.6, 1.0, 0.8)
            cr.set_line_width(1.5)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            cr.restore()
            return

        if self._selected_span is None:
            return
        bbox = self._selected_span.bbox
        x = bbox[0] * scale + scroll_x
        y = bbox[1] * scale + scroll_y
        w = (bbox[2] - bbox[0]) * scale
        h = (bbox[3] - bbox[1]) * scale

        cr.save()
        cr.set_source_rgba(0.3, 0.6, 1.0, 0.25)
        cr.rectangle(x, y, w, h)
        cr.fill()
        cr.set_source_rgba(0.3, 0.6, 1.0, 0.8)
        cr.set_line_width(1.5)
        cr.rectangle(x, y, w, h)
        cr.stroke()
        cr.restore()

    @property
    def selected_span(self):
        return self._selected_span

    @property
    def has_selection(self):
        return self._selected_span is not None or self._selected_annot is not None
