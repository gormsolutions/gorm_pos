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


# gormsolutions_mobile_app/custom_api/stock/stock_entry_validation.py
import frappe

@frappe.whitelist()
def validate_stock_entry(doc, method=None):
    """
    Validates Stock Entry before saving.
    Prevents qty entry if s_warehouse is not in the user's default warehouses.
    Skips validation if the item is linked to a Material Request.
    """
    # Get default warehouses dynamically
    allowed_warehouses = get_user_default_warehouse() or []

    for item in doc.items:
        # Skip if item is linked to a Material Request
        if item.get("material_request"):
            continue

        if doc.purpose == "Material Transfer" and doc.docstatus == 0:
            if item.s_warehouse not in allowed_warehouses and item.qty:
                frappe.throw(
                    f"Cannot enter quantity for warehouse '{item.s_warehouse}'. "
                    f"Allowed warehouses: {', '.join(allowed_warehouses)}"
                )

@frappe.whitelist()
def get_user_default_warehouse():
    """
    Get all default warehouses for the logged-in user dynamically
    from Transfer Permitted Warehouse and Permitted Warehouse Items.
    """
    user = frappe.session.user

    parent_records = frappe.get_all(
        "Transfer Permitted Warehouse",
        filters={"user": user},
        pluck="name"
    )

    if not parent_records:
        return []

    default_warehouses = frappe.get_all(
        "Permitted Warehouse Items",
        filters={
            "parent": ["in", parent_records],
            "default": 1
        },
        fields=["warehouse"]
    )

    return [w.warehouse for w in default_warehouses]
