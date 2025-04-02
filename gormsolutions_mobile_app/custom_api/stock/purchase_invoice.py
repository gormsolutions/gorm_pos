import frappe

@frappe.whitelist()
def create_purchase_invoice(supplier, items, posting_date=None, due_date=None, company=None, payments=None):
    """
    Create a Purchase Invoice in Frappe and optionally create partial Payment Entries.
    :param supplier: The supplier for the purchase invoice.
    :param items: A list of dictionaries containing item details (item_code, qty, rate).
    :param posting_date: The posting date of the invoice (optional).
    :param due_date: The due date for payment (optional).
    :param company: The company for which the invoice is created (optional).
    :param payments: A list of dictionaries specifying partial payments (amount, payment_account).
    :return: A success message or error details.
    """
    try:
        # Create a new Purchase Invoice document
        purchase_invoice = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": supplier,
            "posting_date": posting_date or frappe.utils.nowdate(),
            "due_date": due_date or frappe.utils.add_days(frappe.utils.nowdate(), 30),  # Default due date is 30 days from posting date
            "company": company or frappe.defaults.get_user_default("Company"),
            "items": [
                {
                    "item_code": item["item_code"],
                    "qty": item["qty"],
                    "uom": item.get("uom"),  # Default UOM is 'Nos'
                    "rate": item["rate"]
                } for item in items
            ]
        })

        # Insert the document into the database
        purchase_invoice.insert()
        # Submit the document
        purchase_invoice.submit()

        # Handle partial payments if provided
        payment_entries = []
        if payments:
            for payment in payments:
                if not payment.get("amount") or not payment.get("payment_account"):
                    return {
                        "status": "error",
                        "message": "Each payment must include 'amount' and 'payment_account'."
                    }

                # Create a Payment Entry document
                payment_entry = frappe.get_doc({
                    "doctype": "Payment Entry",
                    "payment_type": "Pay",
                    "party_type": "Supplier",
                    "party": supplier,
                    "posting_date": posting_date or frappe.utils.nowdate(),
                    "company": company or frappe.defaults.get_user_default("Company"),
                    "paid_from": payment["payment_account"],
                    "paid_to": frappe.db.get_value("Company", company or frappe.defaults.get_user_default("Company"), "default_payable_account"),
                    "paid_amount": payment["amount"],
                    "received_amount": payment["amount"],
                    "references": [
                        {
                            "reference_doctype": "Purchase Invoice",
                            "reference_name": purchase_invoice.name,
                            "total_amount": purchase_invoice.grand_total,
                            "outstanding_amount": purchase_invoice.outstanding_amount,
                            "allocated_amount": payment["amount"]
                        }
                    ]
                })

                # Insert and submit the Payment Entry
                payment_entry.insert()
                payment_entry.submit()
                payment_entries.append(payment_entry.name)

        return {
            "status": "success",
            "message": f"Purchase Invoice {purchase_invoice.name} created successfully.",
            "invoice_name": purchase_invoice.name,
            "payment_entries": payment_entries
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error creating Purchase Invoice or Payment Entry")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }
        
        
        
#         {
#     "supplier": "TEST SUPPLIER",
#     "items": [
#         {"item_code": "Test Item", "qty": 10, "rate": 50,"uom":"Nos"}
#     ],
#     "posting_date": "2025-04-01",
#     "due_date": "2025-05-01",
#     "payments": [
#         {"amount": 500, "payment_account": "1310 - Cash accounts - SD"}

#     ]
# }