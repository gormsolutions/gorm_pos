import frappe

@frappe.whitelist()
def create_purchase_order(supplier, items, transaction_date=None, schedule_date=None, company=None):
    """
    Create a Purchase Order in Frappe.
    :param supplier: The supplier for the purchase order.
    :param items: A list of dictionaries containing item details (item_code, qty, rate).
    :param transaction_date: The date of the purchase order (optional).
    :param schedule_date: The schedule date for delivery (optional).
    :param company: The company for which the purchase order is created (optional).
    :return: A success message or error details.
    """
    try:
        # Create a new Purchase Order document
        purchase_order = frappe.get_doc({
            "doctype": "Purchase Order",
            "supplier": supplier,
            "transaction_date": transaction_date or frappe.utils.nowdate(),
            "schedule_date": schedule_date or frappe.utils.nowdate(),
            "company": company or frappe.defaults.get_user_default("Company"),
            "items": [
                {
                    "item_code": item["item_code"],
                    "qty": item["qty"],
                    "rate": item["rate"],
                    "uom": item.get("uom")  # Default UOM is 'Nos'
                } for item in items
            ]
        })

        # Insert the document into the database
        purchase_order.insert()
        # Submit the document
        purchase_order.submit()

        return {
            "status": "success",
            "message": f"Purchase Order {purchase_order.name} created successfully.",
            "order_name": purchase_order.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error creating Purchase Order")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }

@frappe.whitelist()
def create_purchase_order_invoice_and_payment(supplier, items, transaction_date=None, schedule_date=None, company=None, payments=None):
    """
    Create a Purchase Order in Frappe, create a Purchase Invoice against it, and optionally create Payment Entries.
    :param supplier: The supplier for the purchase order.
    :param items: A list of dictionaries containing item details (item_code, qty, rate).
    :param transaction_date: The date of the purchase order (optional).
    :param schedule_date: The schedule date for delivery (optional).
    :param company: The company for which the purchase order is created (optional).
    :param payments: A list of dictionaries specifying payments (amount, payment_account, mode_of_payment).
    :return: A success message or error details.
    """
    try:
        # Step 1: Create a Purchase Order
        purchase_order = frappe.get_doc({
            "doctype": "Purchase Order",
            "supplier": supplier,
            "transaction_date": transaction_date or frappe.utils.nowdate(),
            "schedule_date": schedule_date or frappe.utils.nowdate(),
            "company": company or frappe.defaults.get_user_default("Company"),
            "items": [
                {
                    "item_code": item["item_code"],
                    "qty": item["qty"],
                    "rate": item["rate"],
                    "uom": item.get("uom", "Nos"),  # Default UOM is 'Nos'
                    "warehouse": "Main Store Kumi Road - SD"  # Set warehouse to 'Main Store Kumi Road - SD'
                } for item in items
            ]
        })

        # Insert and submit the Purchase Order
        purchase_order.insert()
        purchase_order.submit()

        # Step 2: Create a Purchase Invoice against the Purchase Order
        purchase_invoice = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": supplier,
            "posting_date": transaction_date or frappe.utils.nowdate(),
            "due_date": frappe.utils.add_days(transaction_date or frappe.utils.nowdate(), 30),  # Default due date is 30 days from posting date
            "company": company or frappe.defaults.get_user_default("Company"),
            "items": [
                {
                    "item_code": item["item_code"],
                    "qty": item["qty"],
                    "rate": item["rate"],
                    "uom": item.get("uom", "Nos"),  # Default UOM is 'Nos'
                    "warehouse": "Main Store Kumi Road - SD",  # Set warehouse to 'Main Store Kumi Road - SD'
                    "purchase_order": purchase_order.name  # Link the Purchase Order
                } for item in items
            ]
        })

        # Insert and submit the Purchase Invoice
        purchase_invoice.insert()
        # purchase_invoice.submit()

        # Step 3: Handle payments if provided
        payment_entries = []
        if payments:
            for payment in payments:
                if not payment.get("amount") or not payment.get("payment_account") or not payment.get("mode_of_payment"):
                    return {
                        "status": "error",
                        "message": "Each payment must include 'amount', 'payment_account', and 'mode_of_payment'."
                    }

                # Create a Payment Entry document
                payment_entry = frappe.get_doc({
                    "doctype": "Payment Entry",
                    "payment_type": "Pay",
                    "party_type": "Supplier",
                    "party": supplier,
                    "posting_date": transaction_date or frappe.utils.nowdate(),
                    "company": company or frappe.defaults.get_user_default("Company"),
                    # "paid_from": payment["payment_account"],
                    "paid_to": frappe.db.get_value("Company", company or frappe.defaults.get_user_default("Company"), "default_payable_account"),
                    "paid_amount": payment["amount"],
                    "received_amount": payment["amount"],
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
            "message": f"Purchase Order {purchase_order.name}, Purchase Invoice {purchase_invoice.name}",
            "order_name": purchase_order.name,
            "invoice_name": purchase_invoice.name,
            "payment_entries": payment_entries
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error creating Purchase Order, Invoice, or Payment")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }