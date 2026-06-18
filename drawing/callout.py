import pymupdf


def draw_callout_on_page(page, box_x0, box_y0, box_x1, box_y1,
                          leader_x, leader_y,
                          color=(0, 0, 0), width=1, text=""):
    page.draw_rect((box_x0, box_y0, box_x1, box_y1), color=color, width=width)

    box_cx = (box_x0 + box_x1) / 2
    box_cy = (box_y0 + box_y1) / 2

    page.draw_line((box_cx, box_cy), (leader_x, leader_y), color=color, width=width)

    if text:
        page.insert_text(
            (box_x0 + 3, box_y0 + 14), text,
            fontsize=10, color=color,
        )
