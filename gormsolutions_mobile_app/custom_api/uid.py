import frappe
import time

def get_unique_invoice_uid():
    """Generate a unique UID for an invoice, guaranteed unique in DB."""
    MAX_RETRIES = 5

    for attempt in range(MAX_RETRIES):
        try:
            uid = frappe.generate_hash(length=12)  # random 12-char UID
            doc = frappe.get_doc({"doctype": "Invoice UID Tracker", "uid": uid})
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            return uid
        except frappe.DuplicateEntryError:
            frappe.db.rollback()
            time.sleep(0.05)  # very short wait
            continue

    raise Exception("Could not generate unique invoice UID after multiple attempts.")
