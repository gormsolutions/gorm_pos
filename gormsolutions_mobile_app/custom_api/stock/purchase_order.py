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
       


import frappe
from frappe.model.document import Document
from frappe import _

@frappe.whitelist(allow_guest=False)
def create_purchase_invoice(supplier, items_json, posting_date=None, due_date=None):
    import json
    try:
        items = json.loads(items_json)  # items_json should be a stringified JSON array
        pi = frappe.new_doc("Purchase Invoice")
        pi.supplier = supplier
        pi.posting_date = posting_date or frappe.utils.today()
        pi.due_date = due_date or frappe.utils.add_days(pi.posting_date, 7)

        for item in items:
            pi.append("items", {
                "item_code": item["item_code"],
                "qty": item["qty"],
                "rate": item["rate"]
            })

        pi.insert()
        pi.submit()

        return {"status": "success", "name": pi.name}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Purchase Invoice API Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def create_purchase_order_invoice_and_payment_ashlink(supplier, items, transaction_date=None, schedule_date=None, company=None, payments=None):
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
                    "warehouse": "Stores - AEL"  # Set warehouse to 'Stores - AEL'
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
                    "warehouse": "Stores - AEL",  # Set warehouse to 'Stores - AELD'
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
   

import frappe
import json
from frappe.utils import today, add_days, nowdate

@frappe.whitelist(allow_guest=False)
def create_purchase_invoices(
    supplier,
    items_json,
    posting_date=None,
    due_date=None,
    warehouse="Main Store Kumi Road - SD",
    payments=None
):
    """
    Create and submit a Purchase Invoice
    Due Date = Posting Date + 30 days
    Payments accept ONLY mode_of_payment
    """

    try:
        if not supplier:
            frappe.throw("Supplier is required")

        # Parse items
        items = json.loads(items_json) if isinstance(items_json, str) else items_json
        if not items or not isinstance(items, list):
            frappe.throw("Items must be a non-empty list")

        # Parse payments
        if payments and isinstance(payments, str):
            payments = json.loads(payments)

        posting_date = posting_date or today()
        due_date = due_date or add_days(posting_date, 30)

        company = frappe.defaults.get_user_default("Company")

        # -----------------------------
        # CREATE PURCHASE INVOICE
        # -----------------------------
        purchase_invoice = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": supplier,
            "posting_date": posting_date,
            "due_date": due_date,
            "company": company,
            "set_warehouse": warehouse,
            "items": []
        })

        for item in items:
            purchase_invoice.append("items", {
                "item_code": item["item_code"],
                "qty": item.get("qty", 1),
                "rate": item.get("rate", 0),
                "uom": item.get("uom", "Nos"),
                "warehouse": warehouse
            })

        purchase_invoice.insert(ignore_permissions=True)
        purchase_invoice.submit()

        # -----------------------------
        # PAYMENTS (MODE OF PAYMENT ONLY)
        # -----------------------------
        payment_entries = []

        if payments:
            default_payable_account = frappe.db.get_value(
                "Company", company, "default_payable_account"
            )

            for payment in payments:
                if not payment.get("amount") or not payment.get("mode_of_payment"):
                    frappe.throw(
                        "Each payment must include: amount, mode_of_payment"
                    )

                paid_from_account = get_mop_default_account(
                    payment["mode_of_payment"], company
                )

                payment_entry = frappe.get_doc({
                    "doctype": "Payment Entry",
                    "payment_type": "Pay",
                    "party_type": "Supplier",
                    "party": supplier,
                    "posting_date": nowdate(),
                    "company": company,
                    "paid_from": paid_from_account,          # 🔑 auto from MOP
                    "paid_to": default_payable_account,
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

                payment_entry.insert(ignore_permissions=True)
                payment_entry.submit()
                payment_entries.append(payment_entry.name)

        return {
            "status": "success",
            "purchase_invoice": purchase_invoice.name,
            "due_date": purchase_invoice.due_date,
            "payments": payment_entries
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Purchase Invoice API Error")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist(allow_guest=False)
def create_payment_for_purchase_invoices(
    purchase_invoice_name,
    posting_date=None,
    payments=None
):
    """
    Create Payment Entries for a Purchase Invoice
    Accepts only mode_of_payment, amount
    """

    try:
        if not purchase_invoice_name:
            frappe.throw("Purchase Invoice Name is required")

        # Fetch Purchase Invoice
        purchase_invoice = frappe.get_doc("Purchase Invoice", purchase_invoice_name)

        # Parse payments JSON if string
        if payments and isinstance(payments, str):
            payments = json.loads(payments)

        posting_date = posting_date or today()
        company = frappe.defaults.get_user_default("Company")

        payment_entries = []

        if payments:
            default_payable_account = frappe.db.get_value(
                "Company", company, "default_payable_account"
            )

            for payment in payments:
                if not payment.get("amount") or not payment.get("mode_of_payment"):
                    frappe.throw(
                        "Each payment must include: amount, mode_of_payment"
                    )

                # Get account automatically from MOP
                paid_from_account = get_mop_default_account(
                    payment["mode_of_payment"], company
                )

                payment_entry = frappe.get_doc({
                    "doctype": "Payment Entry",
                    "payment_type": "Pay",
                    "party_type": "Supplier",
                    "party": purchase_invoice.supplier,
                    "posting_date": posting_date,
                    "company": company,
                    "paid_from": paid_from_account,          # 🔑 from MOP
                    "paid_to": default_payable_account,
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

                payment_entry.insert(ignore_permissions=True)
                payment_entry.submit()
                payment_entries.append(payment_entry.name)

        return {
            "status": "success",
            "purchase_invoice": purchase_invoice.name,
            "due_date": purchase_invoice.due_date,
            "payments": payment_entries
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Purchase Invoice Payment API Error")
        return {
            "status": "error",
            "message": str(e)
        }


def get_mop_default_account(mode_of_payment, company):
    """
    Fetch default account from Mode of Payment child table
    """
    default_account = frappe.db.get_value(
        "Mode of Payment Account",
        {
            "parent": mode_of_payment,
            "company": company
        },
        "default_account"
    )

    if not default_account:
        frappe.throw(
            f"Default Account not set for Mode of Payment '{mode_of_payment}' in company '{company}'"
        )

    return default_account

import frappe
import json
from frappe.utils import nowdate

@frappe.whitelist()
def create_purchase_orders(
    supplier,
    items,
    transaction_date=None,
    schedule_date=None,
    company=None,
    warehouse="Main Store Kumi Road - SD"
):
    """
    Create and submit a Purchase Order in ERPNext
    """

    try:
        # Validate supplier
        if not supplier:
            frappe.throw("Supplier is required")

        # Parse items (string or list)
        if isinstance(items, str):
            items = json.loads(items)

        if not items or not isinstance(items, list):
            frappe.throw("Items must be a non-empty list")

        transaction_date = transaction_date or nowdate()
        schedule_date = schedule_date or nowdate()
        company = company or frappe.defaults.get_user_default("Company")
        warehouse = warehouse or "Main Store Kumi Road - SD"

        # Create Purchase Order
        purchase_order = frappe.get_doc({
            "doctype": "Purchase Order",
            "supplier": supplier,
            "transaction_date": transaction_date,
            "schedule_date": schedule_date,
            "company": company,
            "items": []
        })

        # Add items
        for item in items:
            purchase_order.append("items", {
                "item_code": item.get("item_code"),
                "qty": item.get("qty", 1),
                "rate": item.get("rate", 0),
                "uom": item.get("uom", "Nos"),
                "warehouse": item.get("warehouse", warehouse)
            })

        # Insert & Submit
        purchase_order.insert(ignore_permissions=True)
        purchase_order.submit()

        return {
            "status": "success",
            "purchase_order": purchase_order.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Purchase Order API Error")
        return {
            "status": "error",
            "message": str(e)
        }
