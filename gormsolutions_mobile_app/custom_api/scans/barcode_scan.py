import frappe
from frappe import _

@frappe.whitelist()
def update_item_barcode(item_code, barcode):
    """
    Update barcode for a specific Item.
    Example call:
        POST /api/method/your_app.api.item.update_item_barcode
        {
            "item_code": "ITEM-0001",
            "barcode": "1234567890123"
        }
    """
    if not item_code or not barcode:
        frappe.throw(_("Item Code and Barcode are required."))

    # Fetch the Item
    item = frappe.get_doc("Item", item_code)

    # If barcode child table doesn't exist, create it
    if not hasattr(item, "barcodes"):
        frappe.throw(_("The Item doctype has no barcodes child table."))

    # Clear existing barcodes and add the new one
    item.barcodes = []
    item.append("barcodes", {
        "barcode": barcode
    })

    # Save changes
    item.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": _("Barcode updated successfully"),
        "item_code": item_code,
        "barcode": barcode
    }


import frappe
from frappe import _

@frappe.whitelist()
def get_all_items():
    """
    Fetch all Item codes and names.
    GET /api/method/gormsolutions_mobile_app.custom_api.items.get_all_items
    """
    items = frappe.get_all(
        "Item",
        fields=["name as item_code", "item_name"],
        filters={"disabled": 0},  # optional: only active items
        order_by="item_name asc"
    )
    return items
