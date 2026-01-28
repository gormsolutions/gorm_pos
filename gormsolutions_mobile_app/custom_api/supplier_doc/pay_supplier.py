import frappe
from frappe import _
from frappe.utils import nowdate, getdate

@frappe.whitelist()
def pay_supplier(
    supplier=None,
    amount=None,
    paid_from=None,
    reference_no=None,
    posting_date=None,
    reference_date=None,
    company="ASHLINK ENTERPRISE LTD",
    remarks=None
):
    """
    Create and submit a Payment Entry to pay a Supplier.
    """

    if not supplier or not amount or not paid_from or not company:
        frappe.throw(_("Please provide Supplier, Amount, Paid From account, and Company."))

    # Use dates from Postman, or fallback to today
    posting_date = getdate(posting_date) if posting_date else nowdate()
    reference_date = getdate(reference_date) if reference_date else posting_date

    # Fetch supplier account (Payables)
    supplier_account = frappe.db.get_value(
        "Party Account",
        {"parenttype": "Supplier", "parent": supplier, "company": company},
        "account"
    )
    if not supplier_account:
        supplier_account = frappe.db.get_value(
            "Account",
            {"account_type": "Payable", "company": company},
            "name"
        )
        if not supplier_account:
            frappe.throw(_("No payable account found for this company."))

    # Create Payment Entry
    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Pay"
    pe.party_type = "Supplier"
    pe.custom_remarks = 1
    pe.party = supplier
    pe.posting_date = posting_date
    pe.company = company
    pe.paid_from = paid_from
    pe.paid_to = supplier_account
    pe.paid_amount = amount
    pe.received_amount = amount
    pe.reference_no = reference_no
    pe.reference_date = reference_date
    pe.remarks = remarks or f"Supplier Payment to {supplier}"

    pe.insert(ignore_permissions=True)
    pe.submit()
    frappe.db.commit()

    return {
        "message": "Supplier payment created successfully.",
        "name": pe.name,
        "supplier": supplier,
        "amount": amount,
        "paid_from": paid_from,
        "posting_date": posting_date,
        "reference_date": reference_date
    }
