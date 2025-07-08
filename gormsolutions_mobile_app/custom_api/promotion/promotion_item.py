import frappe
from frappe.utils import today, flt

@frappe.whitelist()
def get_free_items_by_item(item_code, qty, company):
    qty = flt(qty)
    promos = frappe.get_all("Free Item Promotion",
        filters={
            "main_item": item_code,
            "is_active": 1,
            "company": company,
            "valid_from": ["<=", today()],
            "valid_to": [">=", today()]
        },
        fields=["name"]
    )

    free_items = []

    for promo in promos:
        children = frappe.get_all("Free Item Promotion item",
            filters={"parent": promo.name},
            fields=["free_item", "free_qty_per_main_qty"]
        )

        for child in children:
            free_item_code = child.free_item
            free_qty = flt(child.free_qty_per_main_qty) * qty

            # Fetch item_name and stock_uom from Item doctype
            item_details = frappe.get_value("Item", free_item_code,
                ["item_name", "stock_uom"], as_dict=True)

            # Fetch income_account from Item Default child table for this company
            income_account = frappe.db.get_value("Item Default",
                {"parent": free_item_code, "company": company},
                "income_account")

            free_items.append({
                "item_code": free_item_code,
                "item_name": item_details.item_name if item_details else None,
                "uom": item_details.stock_uom if item_details else None,
                "income_account": income_account,
                "qty": free_qty
            })

    return free_items

