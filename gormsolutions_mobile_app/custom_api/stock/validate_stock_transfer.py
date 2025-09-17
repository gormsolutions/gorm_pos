import frappe
from frappe import _
from erpnext.stock.utils import get_latest_stock_qty

def validate_stock_before_transfer(doc, method):
    # Run only if purpose is Material Transfer
    if doc.purpose != "Material Transfer":
        return

    for item in doc.items:
        if not item.s_warehouse:
            continue  # skip if no source warehouse

        # Get current stock balance
        qty = get_latest_stock_qty(item.item_code, item.s_warehouse)

        if item.qty > qty:
            frappe.throw(
                _("Not enough stock for Item {0} in Warehouse {1}. Required: {2}, Available: {3}")
                .format(item.item_code, item.s_warehouse, item.qty, qty)
            )
