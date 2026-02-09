import frappe
from frappe import enqueue

def final_repost_gl_desc():
    """
    Repost all GL and Payment Ledger entries, starting from the most recent.
    Batched, safe, idempotent, runs in long queue.
    """
    # enqueue(_repost_doctype_desc, doctype="Sales Invoice", batch_size=200, queue='long')
    # enqueue(_repost_doctype_desc, doctype="Purchase Invoice", batch_size=200, queue='long')
    # enqueue(_repost_doctype_desc, doctype="Journal Entry", batch_size=200, queue='long')
    enqueue(_repost_doctype_desc, doctype="Payment Entry", batch_size=500, queue='long')


def _repost_doctype_desc(doctype, batch_size=500, offset=0):
    total = frappe.db.count(doctype, {"docstatus": 1})
    
    while offset < total:
        docs = frappe.get_all(
            doctype,
            filters={"docstatus": 1},
            fields=["name"],
            limit=batch_size,
            start=offset,
            order_by="posting_date desc, creation desc"
        )

        for d in docs:
            try:
                doc = frappe.get_doc(doctype, d.name)
                doc.make_gl_entries()  # safe, idempotent
            except Exception as e:
                frappe.log_error(f"Repost failed: {doctype} {d.name}", str(e))

        offset += batch_size
        processed = min(offset, total)
        print(f"{doctype}: processed {processed} / {total}")

        if offset < total:
            enqueue(
                _repost_doctype_desc,
                doctype=doctype,
                batch_size=batch_size,
                offset=offset,
                queue='long'
            )
