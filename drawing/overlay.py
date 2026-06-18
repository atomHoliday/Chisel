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


def draw_preview_callout(cr, bx0, by0, bx1, by1, lx, ly, color=(0, 0, 0), width=1):
    cr.save()
    cr.set_source_rgb(*color)
    cr.set_line_width(width)
    cr.rectangle(bx0, by0, bx1 - bx0, by1 - by0)
    cr.stroke()
    bcx = (bx0 + bx1) / 2
    bcy = (by0 + by1) / 2
    cr.move_to(bcx, bcy)
    cr.line_to(lx, ly)
    cr.stroke()
    cr.restore()
