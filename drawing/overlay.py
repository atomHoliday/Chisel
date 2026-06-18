import math


def draw_preview_line(cr, x0, y0, x1, y1, color=(0, 0, 0), width=1):
    cr.save()
    cr.set_source_rgb(*color)
    cr.set_line_width(width)
    cr.move_to(x0, y0)
    cr.line_to(x1, y1)
    cr.stroke()
    cr.restore()


def draw_preview_arrow(cr, x0, y0, x1, y1, color=(0, 0, 0), width=1):
    cr.save()
    cr.set_source_rgb(*color)
    cr.set_line_width(width)
    cr.move_to(x0, y0)
    cr.line_to(x1, y1)
    cr.stroke()
    angle = math.atan2(y1 - y0, x1 - x0)
    arrow_len = 8 + width * 2
    for sign in (-1, 1):
        ax = x1 - arrow_len * math.cos(angle + sign * 0.5)
        ay = y1 - arrow_len * math.sin(angle + sign * 0.5)
        cr.move_to(x1, y1)
        cr.line_to(ax, ay)
        cr.stroke()
    cr.restore()


def draw_preview_rect(cr, x0, y0, x1, y1, color=(0, 0, 0), width=1, fill=None):
    cr.save()
    if fill:
        cr.set_source_rgba(*fill)
        cr.rectangle(x0, y0, x1 - x0, y1 - y0)
        cr.fill()
    cr.set_source_rgb(*color)
    cr.set_line_width(width)
    cr.rectangle(x0, y0, x1 - x0, y1 - y0)
    cr.stroke()
    cr.restore()


def draw_preview_circle(cr, cx, cy, r, color=(0, 0, 0), width=1, fill=None):
    cr.save()
    if fill:
        cr.set_source_rgba(*fill)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.fill()
    cr.set_source_rgb(*color)
    cr.set_line_width(width)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.stroke()
    cr.restore()


def _compute_box(ox, oy, cx, cy, box_w, box_h):
    """Return (bx0, by0, bx1, by1) positioned relative to drag direction."""
    dx = cx - ox
    dy = cy - oy
    if abs(dx) > abs(dy) * 0.5:
        if dx > 0:
            return cx, cy - box_h / 2, cx + box_w, cy + box_h / 2
        else:
            return cx - box_w, cy - box_h / 2, cx, cy + box_h / 2
    else:
        if dy > 0:
            return cx - box_w / 2, cy, cx + box_w / 2, cy + box_h
        else:
            return cx - box_w / 2, cy - box_h, cx + box_w / 2, cy


def _edge_point(bx0, by0, bx1, by1, ox, oy):
    """Return the edge midpoint on the side of the box facing (ox, oy)."""
    bcx = (bx0 + bx1) / 2
    bcy = (by0 + by1) / 2
    dx = ox - bcx
    dy = oy - bcy
    half_w = max((bx1 - bx0) / 2, 0.001)
    half_h = max((by1 - by0) / 2, 0.001)
    if abs(dx / half_w) > abs(dy / half_h):
        return (bx0, bcy) if dx < 0 else (bx1, bcy)
    else:
        return (bcx, by0) if dy < 0 else (bcx, by1)


def draw_preview_callout(cr, ox, oy, cx, cy, box_w, box_h, text, color=(0, 0, 0), width=1):
    cr.save()

    bx0, by0, bx1, by1 = _compute_box(ox, oy, cx, cy, box_w, box_h)
    bcx = (bx0 + bx1) / 2
    bcy = (by0 + by1) / 2
    rx = (bx1 - bx0) / 2
    ry = (by1 - by0) / 2

    # Origin dot
    cr.set_source_rgb(*color)
    cr.arc(ox, oy, 3, 0, 2 * 3.14159)
    cr.fill()

    # Oval outline
    cr.save()
    cr.translate(bcx, bcy)
    cr.scale(1, ry / rx)
    cr.arc(0, 0, rx, 0, 2 * 3.14159)
    cr.set_line_width(width)
    cr.set_source_rgb(*color)
    cr.stroke()
    cr.restore()

    # Leader line to oval edge
    ex, ey = _edge_point(bx0, by0, bx1, by1, ox, oy)
    cr.move_to(ox, oy)
    cr.line_to(ex, ey)
    cr.stroke()

    # Centered text inside oval
    if text:
        cr.set_font_size(10)
        cr.set_source_rgb(*color)
        text_width = len(text) * 3
        cr.move_to(bcx - text_width / 2, bcy + 3.5)
        cr.show_text(text)

    cr.restore()
