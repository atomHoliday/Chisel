import pymupdf
from tools.base import Tool
from tools.clipboard import get_clipboard
from document.text_model import find_span_at
from drawing.theme import (
    SELECT_FILL, SELECT_BORDER, SELECT_WIDTH,
    PASTE_FILL, PASTE_BORDER, PASTE_WIDTH,
    HANDLE_SIZE, HANDLE_FILL, HANDLE_BORDER, HANDLE_BORDER_WIDTH,
)


class SelectTool(Tool):
    name = "select"

    def __init__(self, canvas, document):
        super().__init__(canvas, document)
        self._selected_span = None
        self._selected_annot = None
        self._selected_annot_page = None
        self._page_num = -1
        self._pending_paste = None
        self._paste_pos = (0, 0)
        self._resize_mode = None
        self._resize_original_rect = None
        self._resize_drag_start = None
        self._resize_preview_rect = None

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
        self._selected_annot_page = None
        self._resize_mode = None
        self._resize_original_rect = None
        self._resize_drag_start = None
        self._resize_preview_rect = None
        self._canvas._selected_item = None
        self._canvas.queue_draw()
        return True

    def on_click(self, x, y, scale, scroll_x, scroll_y):
        if self._pending_paste:
            page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
            self._commit_paste(page_x, page_y)
            return True

        if self._selected_annot is not None and self._page_num == self._canvas.page_num:
            handle = self._hit_test_handles(x, y, scale, scroll_x, scroll_y)
            if handle:
                self._resize_mode = handle
                try:
                    r = self._selected_annot.rect
                    self._resize_original_rect = (r.x0, r.y0, r.x1, r.y1)
                except Exception:
                    self._resize_original_rect = None
                self._resize_drag_start = (x, y)
                self._resize_preview_rect = None
                return True

        page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
        doc = self._document
        if not doc or not doc.is_loaded:
            return False
        page_num = self._canvas.page_num
        self._resize_mode = None
        self._resize_original_rect = None
        self._resize_drag_start = None
        self._resize_preview_rect = None
        span = find_span_at(doc, page_num, page_x, page_y)
        if span:
            self._selected_span = span
            self._selected_annot = None
            self._selected_annot_page = None
            self._page_num = page_num
            self._canvas._selected_item = {"type": "text", "span": span}
            self._canvas.queue_draw()
            return True

        page, annot = self._find_annot_at(doc, page_num, page_x, page_y)
        if annot:
            self._selected_annot = annot
            self._selected_annot_page = page
            self._selected_span = None
            self._page_num = page_num
            self._canvas._selected_item = {"type": "annot", "annot": annot}
            self._canvas.queue_draw()
            return True

        self._selected_span = None
        self._selected_annot = None
        self._selected_annot_page = None
        self._canvas._selected_item = None
        self._canvas.queue_draw()
        return True

    def on_drag_begin(self, x, y, scale, scroll_x, scroll_y):
        if self._pending_paste:
            return True
        if self._resize_mode:
            return True
        return False

    def on_drag_update(self, x, y, scale, scroll_x, scroll_y):
        if self._resize_mode and self._resize_drag_start and self._resize_original_rect:
            sx, sy = self._resize_drag_start
            dx = (x - sx) / scale
            dy = (y - sy) / scale
            new_rect = self._compute_resize(self._resize_mode, dx, dy)
            self._resize_preview_rect = new_rect
            self._canvas.queue_draw()
            return True
        return False

    def on_drag_end(self, x, y, scale, scroll_x, scroll_y):
        if self._pending_paste:
            page_x, page_y = self.canvas_to_page(x, y, scale, scroll_x, scroll_y)
            self._commit_paste(page_x, page_y)
            return True
        if self._resize_mode and self._resize_preview_rect:
            self._apply_resize(self._resize_preview_rect)
            self._canvas._pixbuf = None
            self._canvas.queue_draw()
        self._resize_mode = None
        self._resize_original_rect = None
        self._resize_drag_start = None
        self._resize_preview_rect = None
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
            self._selected_annot_page = None
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
        annots = list(page.annots()) if page.annots() else []
        for annot in reversed(annots):
            try:
                rect = annot.rect
            except Exception:
                continue
            if rect.x0 <= page_x <= rect.x1 and rect.y0 <= page_y <= rect.y1:
                try:
                    _ = annot.type
                except Exception:
                    continue
                return (page, annot)
        return (None, None)

    def _get_resize_handles(self, rect, scale, scroll_x, scroll_y):
        x0, y0, x1, y1 = rect
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        points = {
            "nw": (x0, y0), "n": (cx, y0), "ne": (x1, y0),
            "w": (x0, cy), "e": (x1, cy),
            "sw": (x0, y1), "s": (cx, y1), "se": (x1, y1),
        }
        result = []
        for handle_id, (px, py) in points.items():
            cx_pos = px * scale + scroll_x
            cy_pos = py * scale + scroll_y
            result.append((handle_id, cx_pos, cy_pos))
        return result

    def _hit_test_handles(self, canvas_x, canvas_y, scale, scroll_x, scroll_y):
        if self._selected_annot is None:
            return None
        try:
            rect = (
                self._selected_annot.rect.x0,
                self._selected_annot.rect.y0,
                self._selected_annot.rect.x1,
                self._selected_annot.rect.y1,
            )
        except Exception:
            return None
        handles = self._get_resize_handles(rect, scale, scroll_x, scroll_y)
        for handle_id, hx, hy in handles:
            dist = ((canvas_x - hx) ** 2 + (canvas_y - hy) ** 2) ** 0.5
            if dist <= HANDLE_SIZE:
                return handle_id
        return None

    def _compute_resize(self, handle_id, dx_page, dy_page):
        orig = self._resize_original_rect
        x0, y0, x1, y1 = orig
        min_size = 10.0
        if handle_id == "nw":
            x0 += dx_page
            y0 += dy_page
            if x1 - x0 < min_size:
                x0 = x1 - min_size
            if y1 - y0 < min_size:
                y0 = y1 - min_size
        elif handle_id == "ne":
            x1 += dx_page
            y0 += dy_page
            if x1 - x0 < min_size:
                x1 = x0 + min_size
            if y1 - y0 < min_size:
                y0 = y1 - min_size
        elif handle_id == "sw":
            x0 += dx_page
            y1 += dy_page
            if x1 - x0 < min_size:
                x0 = x1 - min_size
            if y1 - y0 < min_size:
                y1 = y0 + min_size
        elif handle_id == "se":
            x1 += dx_page
            y1 += dy_page
            if x1 - x0 < min_size:
                x1 = x0 + min_size
            if y1 - y0 < min_size:
                y1 = y0 + min_size
        elif handle_id == "n":
            y0 += dy_page
            if y1 - y0 < min_size:
                y0 = y1 - min_size
        elif handle_id == "s":
            y1 += dy_page
            if y1 - y0 < min_size:
                y1 = y0 + min_size
        elif handle_id == "e":
            x1 += dx_page
            if x1 - x0 < min_size:
                x1 = x0 + min_size
        elif handle_id == "w":
            x0 += dx_page
            if x1 - x0 < min_size:
                x0 = x1 - min_size
        return (x0, y0, x1, y1)

    def _apply_resize(self, new_rect):
        annot = self._selected_annot
        if annot is None:
            return
        try:
            annot_type = annot.type[1]
        except Exception:
            return
        if annot_type == "Line":
            orig = self._resize_original_rect
            handle = self._resize_mode
            p1 = (new_rect[0], new_rect[1]) if handle in ("nw", "n", "w") else (orig[0], orig[1])
            p2 = (new_rect[2], new_rect[3]) if handle in ("se", "s", "e") else (orig[2], orig[3])
            try:
                self._document._doc.journal_start_op("resize line")
                page = self._document._doc[self._canvas.page_num]
                annots = list(page.annots()) if page.annots() else []
                for a in annots:
                    if a == annot:
                        rect = pymupdf.Rect(
                            min(p1[0], p2[0]), min(p1[1], p2[1]),
                            max(p1[0], p2[0]), max(p1[1], p2[1]),
                        )
                        a.set_rect(rect)
                        a.set_line_ends(annot.line_ends[0], annot.line_ends[1])
                        a.update()
                        break
                self._document._doc.journal_stop_op()
            except Exception:
                self._document._doc.journal_stop_op()
        else:
            try:
                self._document._doc.journal_start_op("resize annot")
                rect = pymupdf.Rect(new_rect[0], new_rect[1], new_rect[2], new_rect[3])
                annot.set_rect(rect)
                annot.update()
                self._document._doc.journal_stop_op()
            except Exception:
                self._document._doc.journal_stop_op()

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
            except Exception:
                pass
            finally:
                doc.stop_op()
            self._selected_annot = None
            self._selected_annot_page = None
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
        try:
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
        except Exception:
            return None

    def on_copy(self):
        if self._selected_annot is not None:
            data = self._serialize_annot(self._selected_annot)
            if data:
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

    def _draw_resize_handles(self, cr, rect, scale, scroll_x, scroll_y):
        handles = self._get_resize_handles(
            (rect.x0, rect.y0, rect.x1, rect.y1),
            scale, scroll_x, scroll_y,
        )
        half = HANDLE_SIZE / 2
        for handle_id, hx, hy in handles:
            cr.save()
            cr.set_source_rgba(*HANDLE_FILL)
            cr.rectangle(hx - half, hy - half, HANDLE_SIZE, HANDLE_SIZE)
            cr.fill()
            cr.set_source_rgba(*HANDLE_BORDER)
            cr.set_line_width(HANDLE_BORDER_WIDTH)
            cr.rectangle(hx - half, hy - half, HANDLE_SIZE, HANDLE_SIZE)
            cr.stroke()
            cr.restore()

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
            cr.set_source_rgba(*PASTE_FILL)
            cr.rectangle(x, y, pw, ph)
            cr.fill()
            cr.set_source_rgba(*PASTE_BORDER)
            cr.set_line_width(PASTE_WIDTH)
            cr.rectangle(x, y, pw, ph)
            cr.stroke()
            cr.restore()
            return

        if self._page_num != self._canvas.page_num:
            return

        if self._canvas._selected_item is None:
            self._selected_annot = None
            self._selected_annot_page = None
            self._selected_span = None

        if self._selected_annot is not None:
            try:
                r = self._selected_annot.rect
            except Exception:
                self._selected_annot = None
                self._selected_annot_page = None
                self._canvas._selected_item = None
                return
            x = r.x0 * scale + scroll_x
            y = r.y0 * scale + scroll_y
            w = (r.x1 - r.x0) * scale
            h = (r.y1 - r.y0) * scale
            cr.save()
            cr.set_source_rgba(*SELECT_FILL)
            cr.rectangle(x, y, w, h)
            cr.fill()
            cr.set_source_rgba(*SELECT_BORDER)
            cr.set_line_width(SELECT_WIDTH)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            if self._resize_preview_rect:
                pr = self._resize_preview_rect
                px = pr[0] * scale + scroll_x
                py = pr[1] * scale + scroll_y
                pw = (pr[2] - pr[0]) * scale
                ph = (pr[3] - pr[1]) * scale
                cr.set_dash([4, 4])
                cr.set_source_rgba(*SELECT_BORDER)
                cr.set_line_width(1.5)
                cr.rectangle(px, py, pw, ph)
                cr.stroke()
                cr.set_dash([])
            cr.restore()
            self._draw_resize_handles(cr, r, scale, scroll_x, scroll_y)
            return

        if self._selected_span is None:
            return
        bbox = self._selected_span.bbox
        x = bbox[0] * scale + scroll_x
        y = bbox[1] * scale + scroll_y
        w = (bbox[2] - bbox[0]) * scale
        h = (bbox[3] - bbox[1]) * scale

        cr.save()
        cr.set_source_rgba(*SELECT_FILL)
        cr.rectangle(x, y, w, h)
        cr.fill()
        cr.set_source_rgba(*SELECT_BORDER)
        cr.set_line_width(SELECT_WIDTH)
        cr.rectangle(x, y, w, h)
        cr.stroke()
        cr.restore()

    @property
    def selected_span(self):
        return self._selected_span

    @property
    def has_selection(self):
        return self._selected_span is not None or self._selected_annot is not None
