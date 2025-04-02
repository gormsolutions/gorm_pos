import frappe

@frappe.whitelist()
def submit_purchase_invoice_and_pay(invoice_name, payments=None):
    """
    Submit an existing draft Purchase Invoice or collect payments if already submitted.
    :param invoice_name: The name of the Purchase Invoice.
    :param payments: A list of dictionaries specifying payments (amount and mode_of_payment).
    :return: A success message or error details.
    """
    try:
        # Fetch the Purchase Invoice
        purchase_invoice = frappe.get_doc("Purchase Invoice", invoice_name)

        # Check if the invoice is already submitted
        if purchase_invoice.docstatus == 0:
            # Submit the Purchase Invoice if it is in draft state
            purchase_invoice.submit()

        # Handle payments if provided
        payment_entries = []
        if payments:
            for payment in payments:
                if not payment.get("amount") or not payment.get("mode_of_payment"):
                    return {
                        "status": "error",
                        "message": "Each payment must include 'amount' and 'mode_of_payment'."
                    }

                # Fetch the Mode of Payment and its default account
                mode_of_payment_doc = frappe.get_doc("Mode of Payment", payment["mode_of_payment"])
                if not mode_of_payment_doc.accounts:
                    return {
                        "status": "error",
                        "message": f"Mode of Payment '{payment['mode_of_payment']}' does not have a default account configured."
                    }

                # Get the Paid From account and its currency
                paid_from_account = mode_of_payment_doc.accounts[0].default_account
                paid_from_account_currency = frappe.db.get_value("Account", paid_from_account, "account_currency")

                # Fetch the company's default currency
                company_currency = frappe.db.get_value("Company", purchase_invoice.company, "default_currency")
                invoice_currency = purchase_invoice.currency

                # Determine the exchange rate
                exchange_rate = 1.0  # Default exchange rate for same currency
                if invoice_currency != company_currency:
                    exchange_rate = frappe.db.get_value(
                        "Currency Exchange",
                        {"from_currency": invoice_currency, "to_currency": company_currency},
                        "exchange_rate"
                    )
                    if not exchange_rate:
                        return {
                            "status": "error",
                            "message": f"Exchange rate not found for {invoice_currency} to {company_currency}."
                        }

                # Create a Payment Entry document
                payment_entry = frappe.get_doc({
                    "doctype": "Payment Entry",
                    "payment_type": "Pay",
                    "party_type": "Supplier",
                    "party": purchase_invoice.supplier,
                    "posting_date": frappe.utils.nowdate(),
                    "company": purchase_invoice.company,
                    "paid_from": paid_from_account,
                    "paid_from_account_currency": paid_from_account_currency,
                    "paid_amount": payment["amount"],
                    "received_amount": payment["amount"] * exchange_rate,
                    "source_exchange_rate": exchange_rate,
                    "mode_of_payment": payment["mode_of_payment"],
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
            "message": f"Purchase Invoice {purchase_invoice.name} processed successfully.",
            "invoice_name": purchase_invoice.name,
            "payment_entries": payment_entries
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error processing Purchase Invoice or creating Payment Entry")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }