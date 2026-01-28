import frappe
from frappe.utils import add_days, nowdate

# @frappe.whitelist()
# def make_sales_invoice_return(sales_invoice_name, posting_date=None, return_items=None):
#     """
#     Create a Sales Invoice Return against a submitted Sales Invoice.
    
#     :param sales_invoice_name: The name (ID) of the submitted Sales Invoice
#     :param return_items: Optional list of dicts with {"item_code": ..., "qty": ..., "rate": ..., "batch_no": ...}
#                          If not provided, full return of all items (with batch numbers) will be created.
#     :return: Success message and new Sales Invoice Return details
#     """
#     # Load the original sales invoice
#     original_si = frappe.get_doc("Sales Invoice", sales_invoice_name)

#     if not original_si.docstatus == 1:
#         frappe.throw("You can only return a submitted Sales Invoice.")

#     # Check if all items are already fully returned
#     returned_qty_map = {}
#     existing_returns = frappe.get_all(
#         "Sales Invoice",
#         filters={"return_against": sales_invoice_name, "docstatus": 1},
#         fields=["name"]
#     )
#     for ret in existing_returns:
#         ret_doc = frappe.get_doc("Sales Invoice", ret.name)
#         for item in ret_doc.items:
#             returned_qty_map[item.item_code] = returned_qty_map.get(item.item_code, 0) + abs(item.qty)

#     fully_returned = True
#     for item in original_si.items:
#         returned_qty = returned_qty_map.get(item.item_code, 0)
#         if returned_qty < item.qty:
#             fully_returned = False
#             break

#     if fully_returned:
#         frappe.throw(f"All items in Sales Invoice {sales_invoice_name} have already been fully returned.")

#     # Create a new Sales Invoice as return
#     return_si = frappe.new_doc("Sales Invoice")
#     return_si.is_return = 1
#     return_si.return_against = original_si.name
#     return_si.customer = original_si.customer
#     return_si.company = original_si.company
#     return_si.posting_date = posting_date if posting_date else nowdate()
#     return_si.due_date = add_days(return_si.posting_date, 3)
#     return_si.set_posting_time = 1
#     return_si.currency = original_si.currency
#     return_si.selling_price_list = original_si.selling_price_list

#     # If custom items passed
#     if return_items:
#         for i in return_items:
#             item_doc = frappe.get_doc("Item", i.get("item_code"))
#             qty = -abs(i.get("qty", 1))
#             rate = i.get("rate", 0)
#             batch_no = i.get("batch_no")

#             # Check batch requirement
#             if item_doc.has_batch_no and not batch_no:
#                 frappe.throw(f"Batch No is mandatory for Item {item_doc.item_code}")

#             return_si.append("items", {
#                 "item_code": item_doc.item_code,
#                 "qty": qty,
#                 "rate": rate,
#                 "batch_no": batch_no if batch_no else None,
#                 "use_serial_batch_fields": 1 if (i.get("batch_no") or i.get("serial_no")) else 0
#             })

#     else:
#         # Default: copy all items from original invoice (with batch numbers)
#         for item in original_si.items:
#             item_doc = frappe.get_doc("Item", item.item_code)
#             qty = -abs(item.qty - returned_qty_map.get(item.item_code, 0))
#             if qty == 0:
#                 continue  # Skip items already fully returned

#             if item_doc.has_batch_no and not item.batch_no:
#                 frappe.throw(f"Original Sales Invoice Item {item.item_code} requires a Batch No but none was found.")

#             return_si.append("items", {
#                 "item_code": item.item_code,
#                 "qty": qty,
#                 "rate": item.rate,
#                 "batch_no": item.batch_no if item_doc.has_batch_no else None
#             })

#     # Copy taxes
#     for tax in original_si.taxes:
#         return_si.append("taxes", {
#             "charge_type": tax.charge_type,
#             "account_head": tax.account_head,
#             "rate": tax.rate,
#             "description": tax.description
#         })

#     # Insert and submit
#     return_si.insert(ignore_permissions=True)
#     return_si.submit()

#     return {
#         "success": True,
#         "message": f"Sales Invoice Return {return_si.name} created successfully.",
#         "sales_invoice_return": return_si.as_dict()
#     }


import frappe
from frappe.utils import add_days, nowdate

@frappe.whitelist()
def make_sales_invoice_return(sales_invoice_name, posting_date=None, return_items=None):
    """
    Create a Sales Invoice Return against a submitted Sales Invoice.
    """

    # ------------------------------------------------------------
    # 1) Check if original invoice exists
    # ------------------------------------------------------------
    if not frappe.db.exists("Sales Invoice", sales_invoice_name):
        frappe.throw(f"Sales Invoice {sales_invoice_name} does not exist.", title="Not Found")

    original_si = frappe.get_doc("Sales Invoice", sales_invoice_name)

    if original_si.docstatus != 1:
        frappe.throw("You can only return a submitted Sales Invoice.")

    # ------------------------------------------------------------
    # 2) Map of original items
    # ------------------------------------------------------------
    original_items_map = {item.item_code: item for item in original_si.items}

    # ------------------------------------------------------------
    # 3) Check already returned quantities
    # ------------------------------------------------------------
    returned_qty_map = {}
    existing_returns = frappe.get_all(
        "Sales Invoice",
        filters={"return_against": sales_invoice_name, "docstatus": 1},
        fields=["name"]
    )

    for ret in existing_returns:
        ret_doc = frappe.get_doc("Sales Invoice", ret.name)
        for item in ret_doc.items:
            returned_qty_map[item.item_code] = returned_qty_map.get(item.item_code, 0) + abs(item.qty)

    fully_returned = True
    for item in original_si.items:
        returned_qty = returned_qty_map.get(item.item_code, 0)
        if returned_qty < item.qty:
            fully_returned = False
            break

    if fully_returned:
        frappe.throw(f"All items in Sales Invoice {sales_invoice_name} have already been fully returned.")

    # ------------------------------------------------------------
    # 4) Create new return Sales Invoice
    # ------------------------------------------------------------
    return_si = frappe.new_doc("Sales Invoice")
    return_si.is_return = 1
    return_si.return_against = original_si.name
    return_si.customer = original_si.customer
    return_si.company = original_si.company
    return_si.posting_date = posting_date if posting_date else nowdate()
    return_si.due_date = add_days(return_si.posting_date, 3)
    return_si.set_posting_time = 1
    return_si.currency = original_si.currency
    return_si.selling_price_list = original_si.selling_price_list
    return_si.update_stock = 1  # Enable stock update

    invoice_cost_center = getattr(original_si, "cost_center", None)
    if invoice_cost_center:
        return_si.cost_center = invoice_cost_center

    # ------------------------------------------------------------
    # 5) Add Items
    # ------------------------------------------------------------
    if return_items:
        for i in return_items:
            item_code = i.get("item_code")
            if item_code not in original_items_map:
                frappe.throw(f"Returned Item {item_code} does not exist in Sales Invoice {sales_invoice_name}")

            original_item = original_items_map[item_code]
            item_doc = frappe.get_doc("Item", item_code)
            qty = -abs(i.get("qty", 1))
            rate = i.get("rate", original_item.rate)
            batch_no = i.get("batch_no") or original_item.batch_no

            if item_doc.has_batch_no and not batch_no:
                frappe.throw(f"Batch No is mandatory for Item {item_doc.item_code}")

            return_si.append("items", {
                "item_code": item_doc.item_code,
                "qty": qty,
                "rate": rate,
                "batch_no": batch_no,
                "use_serial_batch_fields": 1 if (i.get("batch_no") or i.get("serial_no")) else 0,
                "cost_center": invoice_cost_center
            })
    else:
        for item in original_si.items:
            qty = -abs(item.qty - returned_qty_map.get(item.item_code, 0))
            if qty == 0:
                continue

            item_doc = frappe.get_doc("Item", item.item_code)
            if item_doc.has_batch_no and not item.batch_no:
                frappe.throw(f"Original Sales Invoice Item {item.item_code} requires a Batch No.")

            return_si.append("items", {
                "item_code": item.item_code,
                "qty": qty,
                "rate": item.rate,
                "batch_no": item.batch_no if item_doc.has_batch_no else None,
                "cost_center": invoice_cost_center
            })

    # ------------------------------------------------------------
    # 6) Copy Taxes
    # ------------------------------------------------------------
    for tax in original_si.taxes:
        return_si.append("taxes", {
            "charge_type": tax.charge_type,
            "account_head": tax.account_head,
            "rate": tax.rate,
            "description": tax.description
        })

    # ------------------------------------------------------------
    # 7) POS Payments
    # ------------------------------------------------------------
    if original_si.is_pos:
        return_si.is_pos = 1
        for pay in original_si.payments:
            return_si.append("payments", {
                "mode_of_payment": pay.mode_of_payment,
                "amount": abs(pay.amount)
            })

    # ------------------------------------------------------------
    # 8) Save and Submit
    # ------------------------------------------------------------
    return_si.insert(ignore_permissions=True)
    return_si.submit()

    # ------------------------------------------------------------
    # 9) Create Refund Payment Entry (Automatic, Safe)
    # ------------------------------------------------------------
    payment_entries = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": original_si.name},
        fields=["parent", "allocated_amount"]
    )

    if payment_entries:
        pe_ref = payment_entries[0]
        original_pe = frappe.get_doc("Payment Entry", pe_ref.parent)

        refund_pe = frappe.new_doc("Payment Entry")
        refund_pe.payment_type = "Pay"
        refund_pe.company = original_si.company
        refund_pe.posting_date = posting_date or nowdate()
        refund_pe.mode_of_payment = original_pe.mode_of_payment
        refund_pe.party_type = "Customer"
        refund_pe.party = original_si.customer
        refund_pe.cost_center = invoice_cost_center
        refund_pe.paid_from = original_pe.paid_to
        refund_pe.paid_to = original_pe.paid_from
        refund_pe.paid_amount = abs(return_si.rounded_total)
        refund_pe.received_amount = abs(return_si.rounded_total)

        # ❌ Do not allocate to invoice to avoid "Allocated Amount > Outstanding" error
        refund_pe.references = []
        refund_pe.unallocated_amount = abs(return_si.rounded_total)
        refund_pe.allocate_payment_amount = 0

        refund_pe.insert(ignore_permissions=True)
        refund_pe.submit()

    # ------------------------------------------------------------
    return {
        "success": True,
        "message": f"Sales Invoice Return {return_si.name} created successfully.",
        "sales_invoice_return": return_si.as_dict()
    }
