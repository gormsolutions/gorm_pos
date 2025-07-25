# File: my_app/api/item_utils.py or Server Script

import frappe
from frappe import _

@frappe.whitelist()
def disable_unreconciled_items(stock_reco_name):
    reco_doc = frappe.get_doc("Stock Reconciliation", stock_reco_name)
    reco_items = {item.item_code for item in reco_doc.items}

    all_items = frappe.get_all("Item", filters={"disabled": 0}, fields=["name"])
    disabled_count = 0

    for item in all_items:
        if item.name not in reco_items:
            frappe.db.set_value("Item", item.name, "disabled", 1)
            disabled_count += 1

    return _("Disabled {0} items not in {1}").format(disabled_count, stock_reco_name)


import frappe
from frappe import _

@frappe.whitelist()
def update_items_from_stock_reco():
    stock_reco_list = [
        "MAT-RECO-2025-00076"
    ]

    updated_items = set()

    for docname in stock_reco_list:
        doc = frappe.get_doc("Stock Reconciliation", docname)
        for row in doc.items:
            if row.item_code:
                updated_items.add(row.item_code)

    for item_code in updated_items:
        frappe.db.set_value("Item", item_code, "custom_on_selling_pos", 1)

    frappe.db.commit()
    return {
        "message": f"{len(updated_items)} items updated successfully.",
        "items": list(updated_items)
    }

# your_app/item_hooks.py
import frappe

def update_item_price(doc, method):
    if doc.custom_item_price:
        uom = doc.stock_uom or "Nos"  # fallback if stock_uom is not set

        existing_price = frappe.db.exists("Item Price", {
            "item_code": doc.item_code,
            "price_list": "Standard Selling",
            "uom": uom
        })

        if existing_price:
            frappe.db.set_value("Item Price", existing_price, {
                "price_list_rate": doc.custom_item_price,
                "uom": uom
            })
        else:
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": doc.item_code,
                "price_list": "Standard Selling",
                "price_list_rate": doc.custom_item_price,
                "uom": uom
            }).insert(ignore_permissions=True)

