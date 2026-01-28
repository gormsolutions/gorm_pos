import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def cancel_amend_update_submit_invoice(invoice_name, updates=None):
    """
    Cancel an existing Sales Invoice (if not already cancelled), create an amended draft,
    apply updates (including items and payments), recalc totals, and submit it.

    :param invoice_name: The Sales Invoice ID/name to cancel and amend
    :param updates: dict of fields to update in the amended invoice, 
                    e.g. {
                        "customer": "New Customer",
                        "posting_date": "2025-11-18",
                        "items": [{"item_code":..., "qty":..., "rate":...}],
                        "payments": [{"mode_of_payment":..., "amount":...}]
                    }
    :return: Name of the submitted amended Sales Invoice
    """

    # Fetch the original invoice
    invoice = frappe.get_doc("Sales Invoice", invoice_name)

    # Cancel the original invoice if not already cancelled
    if invoice.docstatus != 2:
        invoice.cancel()
        frappe.db.commit()

    # Create amended draft
    amended_invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "amended_from": invoice_name,
        "posting_date": nowdate()
    })

    # Copy fields from the original invoice (except system/meta fields)
    for field in invoice.meta.get("fields"):
        fieldname = field.fieldname
        if fieldname not in ["name", "creation", "modified", "modified_by", "amended_from", "docstatus"]:
            amended_invoice.set(fieldname, invoice.get(fieldname))

    # Insert draft
    amended_invoice.insert()

    # Apply updates if provided
    if updates:
        for field, value in updates.items():
            if field == "items":
                # Clear existing items
                amended_invoice.items = []
                for item in value:
                    amended_invoice.append("items", item)

            elif field == "payments" and hasattr(amended_invoice, "payments"):
                # Clear existing payments
                amended_invoice.payments = []

                for payment in value:
                    if "mode_of_payment" in payment and payment["mode_of_payment"]:
                        # Fetch default account from child table "Mode of Payment Account"
                        mp_accounts = frappe.get_all(
                            "Mode of Payment Account",
                            filters={
                                "parent": payment["mode_of_payment"],
                                "parenttype": "Mode of Payment",
                                "parentfield": "accounts"},
                            fields=["default_account"]
                        )

                        if not mp_accounts:
                            frappe.throw(f"No default account defined for Mode of Payment: {payment['mode_of_payment']}")

                        payment["account"] = mp_accounts[0]["default_account"]

                    amended_invoice.append("payments", payment)

            else:
                amended_invoice.set(field, value)

    # Recalculate taxes and totals
    amended_invoice.set_missing_values()
    amended_invoice.calculate_taxes_and_totals()

    # Submit the amended invoice
    amended_invoice.submit()
    frappe.db.commit()

    return amended_invoice.name
