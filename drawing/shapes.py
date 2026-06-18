import pymupdf


def draw_line_on_page(page, x0, y0, x1, y1, color=(0, 0, 0), width=1, dashes=None):
    page.draw_line((x0, y0), (x1, y1), color=color, width=width, dashes=dashes)


def draw_arrow_on_page(page, x0, y0, x1, y1, color=(0, 0, 0), width=1):
    page.draw_line((x0, y0), (x1, y1), color=color, width=width)
    angle = __import__("math").atan2(y1 - y0, x1 - x0)
    arrow_len = 8 + width * 2
    for sign in (-1, 1):
        ax = x1 - arrow_len * __import__("math").cos(angle + sign * 0.5)
        ay = y1 - arrow_len * __import__("math").sin(angle + sign * 0.5)
        page.draw_line((x1, y1), (ax, ay), color=color, width=width)


def draw_rect_on_page(page, x0, y0, x1, y1, color=(0, 0, 0), width=1, fill=None):
    if fill:
        page.draw_rect((x0, y0, x1, y1), color=fill, width=0, fill=fill)
    page.draw_rect((x0, y0, x1, y1), color=color, width=width)


def draw_circle_on_page(page, cx, cy, r, color=(0, 0, 0), width=1, fill=None):
    if fill:
        page.draw_circle((cx, cy), r, color=fill, width=0, fill=fill)
    page.draw_circle((cx, cy), r, color=color, width=width)
