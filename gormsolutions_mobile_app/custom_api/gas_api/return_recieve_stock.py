# -*- coding: utf-8 -*-
import frappe
import json
from frappe.utils import nowdate, cint

@frappe.whitelist()
def create_purchase_invoice_or_return(supplier, items, is_return=False, posting_date=None):
    if isinstance(items, str):
        items = json.loads(items)

    is_return = cint(is_return)
    posting_date = posting_date or nowdate()
    current_user = frappe.session.user

    # Get permitted warehouse (main)
    permitted_warehouse = frappe.get_all(
        'User Permission',
        filters={'user': current_user, 'allow': 'Warehouse', 'is_default': 1},
        fields=['for_value']
    )
    permitted_warehouse = permitted_warehouse[0]['for_value'] if permitted_warehouse else None

    # Get permitted warehouse (empties)
    permitted_warehouse_empties = frappe.get_all(
        'User Permission',
        filters={'user': current_user, 'allow': 'Warehouse', 'is_default': 0},
        fields=['for_value']
    )
    permitted_warehouse_empties = permitted_warehouse_empties[0]['for_value'] if permitted_warehouse_empties else None

    # Fallbacks
    default_warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse')
    if is_return and not permitted_warehouse_empties:
        permitted_warehouse_empties = default_warehouse
    if not is_return and not permitted_warehouse:
        permitted_warehouse = default_warehouse

    if is_return and not permitted_warehouse_empties:
        return {"error": "No return warehouse assigned to user and no default warehouse set."}
    if not is_return and not permitted_warehouse:
        return {"error": "No warehouse assigned to user and no default warehouse set."}

    # Get permitted cost center
    permitted_cost_center = frappe.get_all(
        'User Permission',
        filters={'user': current_user, 'allow': 'Cost Center', 'is_default': 1},
        fields=['for_value']
    )
    permitted_cost_center = permitted_cost_center[0]['for_value'] if permitted_cost_center else None

    if not permitted_cost_center:
        permitted_cost_center = frappe.db.get_single_value('Company', 'cost_center')
        if not permitted_cost_center:
            return {"error": "No cost center assigned to user and no default found in Company settings."}

    # Create Purchase Invoice
    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = supplier
    pi.posting_date = posting_date
    pi.due_date = posting_date
    pi.set_posting_time = 1
    pi.cost_center = permitted_cost_center
    pi.set_warehouse = permitted_warehouse_empties if is_return else permitted_warehouse
    pi.update_stock = 1
    pi.is_return = is_return

    for item in items:
        item_code = item["item_code"]
        qty = -abs(item["qty"]) if is_return else abs(item["qty"])
        rate = item.get("rate", 0)
        cost_center = item.get("cost_center", permitted_cost_center)

        # Fetch custom fields from Item DocType
        attached_item = frappe.db.get_value("Item", item_code, "custom_attached_item")
        custom_extras = frappe.db.get_value("Item", item_code, "custom_extras")

        # Determine correct warehouse
        if custom_extras == 1:
            item_warehouse = permitted_warehouse  # Only main warehouse
        else:
            item_warehouse = item.get("warehouse") or (permitted_warehouse_empties if is_return else permitted_warehouse)

        # Append the main item
       
        pi.append("items", {
            "item_code": item_code,
            "qty": qty,
            "rate": rate,
            "warehouse": permitted_warehouse if custom_extras == 1 or attached_item else item_warehouse,
            "cost_center": cost_center
        })
            

        # Append the attached item if exists
        if attached_item:
            attached_rate = frappe.db.get_value("Item Price", {
                "item_code": attached_item,
                "buying": 1
            }, "price_list_rate") or 0

            pi.append("items", {
                "item_code": attached_item,
                "qty": qty,
                "rate": attached_rate,
                "warehouse": permitted_warehouse,  # Always use main warehouse for attached item
                "cost_center": cost_center
            })

    pi.insert(ignore_permissions=True)
    pi.submit()

    return {
        "status": "success",
        "is_return": bool(is_return),
        "invoice_name": pi.name,
        "posting_date": pi.posting_date
    }
