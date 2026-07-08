import pymupdf
import os


def insert_image_file(doc, page_num, rect, file_path):
    if doc.doc is None:
        return
    page = doc.doc[page_num]
    page.insert_image(rect, filename=file_path)


def insert_image_bytes(doc, page_num, rect, image_bytes):
    if doc.doc is None:
        return
    page = doc.doc[page_num]
    page.insert_image(rect, stream=image_bytes)


def supported_image_extensions():
    return [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"]


def get_image_natural_size(file_path):
    try:
        pix = pymupdf.Pixmap(file_path)
        size = (pix.width, pix.height)
        pix = None
        return size
    except Exception:
        return None
