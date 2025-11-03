# your_app/permissions.py

import frappe
from frappe import _

@frappe.whitelist()
def prevent_delete(doc, method):
    frappe.log_error(
        message=f"User {frappe.session.user} tried to delete {doc.doctype} {doc.name}",
        title="Unauthorized Delete Attempt"
    )
    frappe.throw(_("You are not allowed to delete this document. It is required for audit trail."))

# permissions.py
import frappe
from frappe import _

@frappe.whitelist()
def prevent_bulk_delete(items, doctype="Deleted Document"):
    # Block bulk deletion for everyone
    frappe.throw(_("Bulk deletion is not allowed. You are not allowed to delete this document. It is required for audit trail."))
