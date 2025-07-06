import frappe
from frappe import _

@frappe.whitelist()
def create_partial_return_invoice(original_invoice, return_items):
    """
    Create a partial return (credit note) from a submitted Sales Invoice.

    :param original_invoice: Sales Invoice name to return against (e.g., "SINV-0001")
    :param return_items: JSON string with list of dicts, each dict must contain:
        - item_code: str
        - qty: float (positive number to return)

    Example return_items:
        '[{"item_code": "ITEM-001", "qty": 1}, {"item_code": "ITEM-002", "qty": 2}]'
    """
    import json

    try:
        return_items = json.loads(return_items)
        original = frappe.get_doc("Sales Invoice", original_invoice)

        if original.docstatus != 1:
            return {
                "status": "error",
                "message": _("Original invoice must be submitted")
            }

        if original.is_return:
            return {
                "status": "error",
                "message": _("Cannot return a return invoice")
            }

        return_invoice = frappe.new_doc("Sales Invoice")
        return_invoice.customer = original.customer
        return_invoice.is_return = 1
        return_invoice.return_against = original.name
        return_invoice.posting_date = frappe.utils.today()
        return_invoice.due_date = original.due_date
        return_invoice.cost_center = original.cost_center
        return_invoice.update_outstanding_for_self = 0
        return_invoice.fulfillment_branch_ = original.fulfillment_branch_
        return_invoice.currency = original.currency
        return_invoice.debit_to = original.debit_to
        return_invoice.selling_price_list = original.selling_price_list
        return_invoice.taxes_and_charges = original.taxes_and_charges
        return_invoice.company = original.company
        return_invoice.customer_address = original.customer_address
        return_invoice.contact_person = original.contact_person
        return_invoice.territory = original.territory

        # Map selected items
        item_lookup = {item.item_code: item for item in original.items}
        for r_item in return_items:
            item_code = r_item.get("item_code")
            qty_to_return = float(r_item.get("qty", 0))

            if item_code in item_lookup and qty_to_return > 0:
                original_item = item_lookup[item_code]

                if qty_to_return > original_item.qty:
                    return {
                        "status": "error",
                        "message": _(f"Cannot return more than sold quantity for item {item_code}")
                    }

                return_invoice.append("items", {
                    "item_code": item_code,
                    "qty": -abs(qty_to_return),
                    "rate": original_item.rate,
                    "uom": original_item.uom,
                    "income_account": original_item.income_account,
                    "cost_center": original_item.cost_center,
                    "warehouse": original_item.warehouse,
                    "description": original_item.description
                })

        if not return_invoice.items:
            return {
                "status": "error",
                "message": _("No valid items found to return.")
            }

        return_invoice.insert(ignore_permissions=True)
        return_invoice.submit()

        return {
            "status": "success",
            "message": _("Partial return invoice created"),
            "return_invoice": return_invoice.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Partial Return Creation Failed")
        return {
            "status": "error",
            "message": _("Failed to create partial return invoice"),
            "error": str(e)
        }
