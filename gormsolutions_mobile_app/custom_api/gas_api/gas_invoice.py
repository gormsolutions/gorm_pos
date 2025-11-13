import frappe
from frappe.model.document import Document
from frappe.exceptions import PermissionError
from datetime import datetime, timedelta

@frappe.whitelist(allow_guest=True)
def create_gas_invoice(customer, items, include_payments=None, remarks=None, mode_of_payment=None):
    try:
        current_user = frappe.session.user

        cost_center_permitted = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Cost Center"},
            fields=["for_value"]
        )
        default_cost_centers = cost_center_permitted[0]['for_value'] if cost_center_permitted else None

        fallback_warehouse = frappe.get_all(
            'User Permission',
            filters={'user': current_user, 'allow': 'Warehouse', "is_default": 1},
            fields=['for_value']
        )
        fallback_warehouse = fallback_warehouse[0]['for_value'] if fallback_warehouse else None

        price_list_permissions = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Price List", "is_default": 1},
            fields=["for_value"]
        )
        price_list = price_list_permissions[0]['for_value'] if price_list_permissions else None

        store_warehouse_empties = frappe.get_all(
            'User Permission',
            filters={'user': current_user, "is_default": 0, 'allow': 'Warehouse'},
            fields=['for_value']
        )
        default_warehouse_empties = store_warehouse_empties[0]['for_value'] if store_warehouse_empties else None

        today_date = datetime.today().date()
        today_time = datetime.now().strftime("%H:%M:%S")
        due_date = today_date + timedelta(days=10)

        total_qty = 0
        grand_totals = 0
        should_submit = True  # default to True

        gas_invoice = frappe.get_doc({
            "doctype": "Gas Invoices",
            "customer": customer,
            "remarks": remarks,
            "station": default_cost_centers,
            "price_list": price_list,
            "mode_of_payment": mode_of_payment,
            "store_for_empties": default_warehouse_empties,
            "store": fallback_warehouse,
            "date": today_date,
            "time": today_time,
            "include_payments": include_payments,
            "due_date": due_date
        })

        for item in items:
            item_code = item.get("item_code")
            qty = item.get("qty", 0)
            rate = item.get("rate", 0)
            discount = item.get("discount_amount") or 0
            discounted_rate = rate - discount
            amount = qty * discounted_rate

            # Fetch UOM
            stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
            uom = item.get("uom") or ("Nos" if item_code == "HORSE PIPE" else stock_uom)

            # Check if it's a Product Bundle
            if frappe.db.exists("Product Bundle", item_code):
                # Get bundled items
                bundled_items = frappe.get_all(
                    "Product Bundle Item",
                    filters={"parent": item_code},
                    fields=["item_code", "qty"]
                )
                for b in bundled_items:
                    total_required = b["qty"] * qty
                    actual_stock = frappe.db.get_value("Bin", {
                        "item_code": b["item_code"],
                        "warehouse": fallback_warehouse
                    }, "actual_qty") or 0

                    if actual_stock < total_required:
                        should_submit = False  # Not enough stock for bundle item
                        frappe.msgprint(f"Insufficient stock for bundled item {b['item_code']}. Required: {total_required}, Available: {actual_stock}")

            gas_invoice.append("items", {
                "item_code": item_code,
                "qty": qty,
                "rate": rate,
                "uom": uom,
                "amount": amount
            })

            total_qty += qty
            grand_totals += amount

        gas_invoice.total_qty = total_qty
        gas_invoice.grand_totals = grand_totals

        gas_invoice.insert(ignore_permissions=True)

        if should_submit:
            gas_invoice.submit()

        frappe.db.commit()
        return {
        "success": "Sales Invoice created and submitted successfully.",
        "invoice_name": gas_invoice.name,
 
         }

    except Exception as e:
        # 🧼 Clean error handling
        frappe_error = getattr(e, 'message', None) or str(e)
        if hasattr(e, 'args') and e.args:
            frappe_error = e.args[0]
        return {"error": f"Failed to create Sales Invoice: {frappe_error}"} 
