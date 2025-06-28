import frappe
from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import RepostItemValuation

@frappe.whitelist()
def force_cancel_repost(docname):
    # Monkey patch the validation method temporarily
    def skip_check(self):
        pass

    RepostItemValuation.check_pending_repost_against_cancelled_transaction = skip_check

    doc = frappe.get_doc("Repost Item Valuation", docname)
    frappe.flags.ignore_permissions = True
    doc.cancel()
    frappe.db.commit()
    return f"Repost Item Valuation {docname} cancelled successfully"
