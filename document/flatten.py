def flatten_annotations(doc):
    if doc._doc is None:
        return
    for page_num in range(doc.page_count):
        page = doc._doc[page_num]
        annot_iter = page.annots()
        annots = list(annot_iter) if annot_iter else []
        for annot in annots:
            page.add_redact_annot(annot.rect)
        page.apply_redactions()
