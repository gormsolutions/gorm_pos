# import frappe
# import json
# from frappe.utils import nowdate, flt

# @frappe.whitelist()
# def create_online_sales_order_with_invoice(
#     customer, items, coupon_code=None, posting_date=None,
#     user=None, is_pos=1, payments=None, mode_of_payment=None, paid_amount=None,
#     reference_no=None
# ):
#     """
#     Create a Sales Order for Online Customers (only 'Online Customer' group),
#     apply coupon code, and automatically create & submit a POS-style Sales Invoice
#     fully linked to the Sales Order, with payments and discounts handled properly.
#     """

#     current_user = user or frappe.session.user

#     # ✅ Require default POS Profile
#     result = frappe.db.sql("""
#         SELECT ppu.parent
#         FROM `tabPOS Profile User` ppu
#         JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
#         WHERE ppu.user = %s AND ppu.default = 1 AND pp.disabled = 0
#         LIMIT 1
#     """, (current_user,), as_dict=0)

#     if not result:
#         frappe.throw(f"User '{current_user}' must have an active default POS Profile assigned.")

#     pos_profile = result[0][0]
#     pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)

#     pos_warehouse = pos_profile_doc.warehouse
#     fulfillment_branch = pos_profile_doc.fulfillment_branch_
#     cost_center = pos_profile_doc.cost_center
#     company = pos_profile_doc.company

#     # ✅ Validate cost center belongs to same company
#     if cost_center:
#         cc_company = frappe.get_value("Cost Center", cost_center, "company")
#         if cc_company and cc_company != company:
#             frappe.throw(
#                 f"Cost Center '{cost_center}' belongs to company '{cc_company}', "
#                 f"but POS Profile '{pos_profile}' is for '{company}'."
#             )

#     # ✅ Customer group check
#     cust_group = frappe.get_value("Customer", customer, "customer_group")
#     if cust_group != "Online Customer":
#         frappe.throw(f"Customer '{customer}' is not in 'Online Customer' group.")

#     # ✅ Warehouse fallback
#     if not pos_warehouse:
#         pos_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
#     if not pos_warehouse:
#         frappe.throw("POS Profile or Stock Settings must define a warehouse.")

#     # Assign warehouse and cost center
#     for item in items or []:
#         item["warehouse"] = pos_warehouse
#         item["cost_center"] = cost_center

#     # ✅ Create Sales Order
#     so = frappe.get_doc({
#         "doctype": "Sales Order",
#         "customer": customer,
#         "company": company,
#         "pos_profile": pos_profile,
#         "set_warehouse": pos_warehouse,
#         "fulfillment_branch_": fulfillment_branch,
#         "cost_center": cost_center,
#         "transaction_date": nowdate(),
#         "delivery_date": nowdate(),
#         "coupon_code": coupon_code,
#         "items": items,
#     })
#     so.run_method("validate")
#     so.save()
#     so.submit()

#     # ✅ Build item mappings (Sales Order Item name to item_code)
#     so_item_map = {d.item_code: d.name for d in so.items}

#     # ✅ Prepare payments
#     payment_entries = []
#     if payments:
#         if isinstance(payments, str):
#             payments = json.loads(payments)
#         for p in payments:
#             amount = flt(p.get("amount") or 0)
#             if amount > 0:
#                 payment_entries.append({
#                     "mode_of_payment": p.get("mode_of_payment"),
#                     "amount": amount,
#                     "reference_no": p.get("reference_no")
#                 })
#     elif mode_of_payment and paid_amount:
#         payment_entries.append({
#             "mode_of_payment": mode_of_payment,
#             "amount": flt(paid_amount),
#             "reference_no": reference_no
#         })

#     # ✅ Prepare invoice items (linked to Sales Order + Sales Order Item)
#     invoice_items = []
#     for item in so.items:
#         invoice_items.append({
#             "item_code": item.item_code,
#             "qty": item.qty,
#             "rate": item.rate,
#             "warehouse": item.warehouse,
#             "cost_center": item.cost_center,
#             "sales_order": so.name,
#             "so_detail": item.name
#         })

#     # ✅ Prepare base invoice data
#     invoice_doc_data = {
#         "doctype": "Sales Invoice",
#         "customer": customer,
#         "company": company,
#         "custom_from": "GormPos",
#         "pos_profile": pos_profile,
#         "fulfillment_branch_": fulfillment_branch,
#         "cost_center": cost_center,
#         "update_stock": 1,
#         "confirm_branch": 1,
#         "is_pos": is_pos,
#         "items": invoice_items,
#         "payments": payment_entries,
#         "apply_discount_on": "Grand Total",
#         "sales_order": so.name,
#         "is_cash_or_non_trade_discount": 1
#     }

#     # ✅ Coupon discount logic
#     discount_account = None
#     if coupon_code:
#         discount_doc = frappe.get_all(
#             "Coupon Code",
#             filters={"custom_company": company, "name": coupon_code},
#             fields=["custom_discount_account"]
#         )
#         if discount_doc:
#             discount_account = discount_doc[0]["custom_discount_account"]

#     # ✅ Apply discount if account exists
#     if discount_account:
#         invoice_doc_data["additional_discount_account"] = discount_account
#         invoice_doc_data["discount_amount"] = flt(so.discount_amount or 0)
#         invoice_doc_data["apply_discount_on"] = "Grand Total"
        
#     else:
#         # Fallback to prevent NoneType crash
#         invoice_doc_data["discount_amount"] = 0.0
        
#     # ✅ Create and submit invoice
#     invoice_doc = frappe.get_doc(invoice_doc_data)
#     # invoice_doc.run_method("validate")
#     invoice_doc.save()
#     invoice_doc.submit()

#     # ✅ Return both references
#     return {
#         "sales_order": so.name,
#         "sales_invoice": invoice_doc.name,
#         "linked_items": [{"so_item": i.so_detail, "si_item": i.name} for i in invoice_doc.items],
#         "sales_invoice_reference": invoice_doc.sales_order
#     }


import frappe
import json
from frappe.utils import nowdate, flt

@frappe.whitelist()
def create_online_sales_invoice(
    customer, items, coupon_code=None, posting_date=None,
    user=None, is_pos=1, payments=None, mode_of_payment=None, paid_amount=None, remarks=None,
    reference_no=None
):
    """
    Create a POS-style Sales Invoice for Online Customers,
    apply coupon code directly on the invoice with discount account,
    and support posting_date. Ensures numeric fields are safe to prevent ERPNext calculation errors.
    """
    current_user = user or frappe.session.user

    # Normalize string inputs
    if remarks: remarks = str(remarks)
    if coupon_code: coupon_code = str(coupon_code)
    if reference_no: reference_no = str(reference_no)

    # --- Default POS Profile ---
    result = frappe.db.sql("""
        SELECT ppu.parent
        FROM `tabPOS Profile User` ppu
        JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
        WHERE ppu.user=%s AND ppu.default=1 AND pp.disabled=0
        LIMIT 1
    """, (current_user,), as_dict=0)

    if not result:
        frappe.throw(f"User '{current_user}' must have an active default POS Profile assigned.")
    pos_profile = result[0][0]
    pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)

    pos_warehouse = pos_profile_doc.warehouse
    fulfillment_branch = pos_profile_doc.fulfillment_branch_
    cost_center = pos_profile_doc.cost_center
    company = pos_profile_doc.company

    # Validate cost center company
    if cost_center:
        cc_company = frappe.get_value("Cost Center", cost_center, "company")
        if cc_company and cc_company != company:
            frappe.throw(f"Cost Center '{cost_center}' belongs to '{cc_company}', "
                         f"but POS Profile '{pos_profile}' is for '{company}'.")

    # Customer group check
    cust_group = frappe.get_value("Customer", customer, "customer_group")
    if cust_group != "Online Customer":
        frappe.throw(f"Customer '{customer}' is not in 'Online Customer' group.")

    # Warehouse fallback
    if not pos_warehouse:
        pos_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
    if not pos_warehouse:
        frappe.throw("POS Profile or Stock Settings must define a warehouse.")

    # --- Prepare invoice items safely ---
    invoice_items = []
    for item in items or []:
        invoice_items.append({
            "item_code": item.get("item_code"),
            "qty": flt(item.get("qty") or 0),
            "rate": flt(item.get("rate") or 0),
            "warehouse": pos_warehouse,
            "cost_center": cost_center
        })

    # --- Prepare payments safely ---
    payment_entries = []
    if payments:
        if isinstance(payments, str):
            payments = json.loads(payments)
        for p in payments:
            amount = flt(p.get("amount") or 0)
            if amount > 0:
                payment_entries.append({
                    "mode_of_payment": p.get("mode_of_payment"),
                    "amount": amount,
                    "reference_no": str(p.get("reference_no") or "")
                })
    elif mode_of_payment and paid_amount:
        payment_entries.append({
            "mode_of_payment": mode_of_payment,
            "amount": flt(paid_amount or 0),
            "reference_no": str(reference_no or "")
        })

    # --- Duplicate prevention ---
    if remarks:
        existing_invoice = frappe.db.exists("Sales Invoice", {"remarks": remarks})
        if existing_invoice:
            return {
                "error": f"Duplicate detected: Invoice with UID '{remarks}' already exists ({existing_invoice}).",
                "status": "duplicate"
            }

    if reference_no:
        ref_exists = frappe.db.get_value("Sales Invoice Payment", {"reference_no": reference_no}, "parent")
        if ref_exists:
            return {
                "error": f"Duplicate payment reference '{reference_no}' already used in invoice {ref_exists}.",
                "status": "duplicate"
            }

    # --- Base invoice data ---
    invoice_doc_data = {
        "doctype": "Sales Invoice",
        "customer": customer,
        "company": company,
        "posting_date": posting_date or nowdate(),
        "custom_from": "GormPos",
        "remarks": remarks,
        "pos_profile": pos_profile,
        "fulfillment_branch_": fulfillment_branch,
        "cost_center": cost_center,
        "update_stock": 1,
        "confirm_branch": 1,
        "is_pos": is_pos,
        "items": invoice_items,
        "payments": payment_entries,
        "apply_discount_on": "Grand Total",
        "is_cash_or_non_trade_discount": 1,
        "discount_amount": 0.0,
        "additional_discount_percentage": 0.0
    }

    # --- Coupon discount ---
    discount_account = None
    discount_amount = 0.0
    discount_percent = 0.0
    if coupon_code:
        discount_doc = frappe.get_all(
            "Coupon Code",
            filters={"custom_company": company, "name": coupon_code},
            fields=["custom_discount_account", "custom_discount_amount", "custom_discount_percent"]
        )
        if discount_doc:
            discount_account = discount_doc[0].get("custom_discount_account")
            discount_amount = flt(discount_doc[0].get("custom_discount_amount") or 0)
            discount_percent = flt(discount_doc[0].get("custom_discount_percent") or 0)

            if discount_account:
                invoice_doc_data["additional_discount_account"] = discount_account
            if discount_amount > 0:
                invoice_doc_data["discount_amount"] = discount_amount
            elif discount_percent > 0:
                invoice_doc_data["additional_discount_percentage"] = discount_percent

            invoice_doc_data["custom_coupon_code"] = str(coupon_code)

    # --- Insert and submit safely ---
    try:
        invoice_doc = frappe.get_doc(invoice_doc_data)

        # Double-check duplicates (concurrent safety)
        if remarks and frappe.db.exists("Sales Invoice", {"remarks": remarks}):
            return {
                "error": f"Duplicate detected at commit for UID '{remarks}'.",
                "status": "duplicate"
            }

        invoice_doc.insert(ignore_permissions=True)
        invoice_doc.submit()
        frappe.db.commit()

        return {
            "sales_invoice": invoice_doc.name,
            "discount_account": discount_account,
            "discount_amount": flt(invoice_doc.discount_amount)
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Online Invoice Creation Error")
        return {
            "error": f"Invoice creation failed: {str(e)}",
            "status": "not_posted"
        }
