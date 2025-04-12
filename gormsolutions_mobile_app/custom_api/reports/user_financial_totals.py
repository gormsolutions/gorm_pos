# import frappe
# from frappe import _

# @frappe.whitelist()
# def get_user_financial_totals(user_email, from_date, to_date):
#     data = {}
#     expense_summary = {}
#     # Branch Expenses created by this user (only submitted)
#     branch_expenses = frappe.db.sql("""
#         SELECT 
#             name, mode_of_payment, grand_total, date, owner AS created_by
#         FROM `tabBranch Expenses`
#         WHERE docstatus = 1 AND owner=%s AND date BETWEEN %s AND %s
#     """, (user_email, from_date, to_date), as_dict=True)
    
#     # Expense Claim Items
#     expense_claim_items = frappe.db.sql("""
#         SELECT sip.claim_type, SUM(sip.amount) as total_amount
#         FROM `tabExpense Claim Items` sip
#         JOIN `tabBranch Expenses` si ON si.name = sip.parent
#         WHERE si.docstatus = 1 AND si.owner = %s AND si.date BETWEEN %s AND %s
#         GROUP BY sip.mode_of_payment
#     """, (user_email, from_date, to_date), as_dict=True)
    
#       # Update accounts summary with sales invoice payment details
#     for eip in expense_claim_items:
#         expense_summary.setdefault(eip["claim_type"], 0)
#         expense_summary[eip["claim_type"]] += eip["total_amount"]

#     # Payment Entries grouped by type and account
#     payment_entries = frappe.db.sql("""
#         SELECT name, party, paid_amount, payment_type, mode_of_payment, paid_from, paid_to, posting_date, owner AS created_by
#         FROM `tabPayment Entry`
#         WHERE docstatus = 1 AND owner=%s AND posting_date BETWEEN %s AND %s
#     """, (user_email, from_date, to_date), as_dict=True)

#     received_payments = [p for p in payment_entries if p["payment_type"] == "Receive"]
#     paid_payments = [p for p in payment_entries if p["payment_type"] == "Pay"]
#     internal_transfers = [p for p in payment_entries if p["payment_type"] == "Internal Transfer"]

#     total_received_amount = sum(p["paid_amount"] for p in received_payments)
#     total_paid_amount = sum(p["paid_amount"] for p in paid_payments)
#     total_internal_transfer_amount = sum(p["paid_amount"] for p in internal_transfers)

#     # Aggregate paid amounts by accounts from Payment Entries
#     accounts_summary = {}

#     for pe in payment_entries:
#         if pe["payment_type"] == "Receive":
#             account = pe["mode_of_payment"]
#         elif pe["payment_type"] == "Pay":
#             account = pe["mode_of_payment"]
#         elif pe["payment_type"] == "Internal Transfer":
#             account = f"{pe['mode_of_payment']} ➝ {pe['paid_to']}"
#         else:
#             account = "Unknown"

#         accounts_summary.setdefault(account, 0)
#         accounts_summary[account] += pe["paid_amount"]

#     # Sales Invoices created by this user (only submitted)
#     sales_invoices = frappe.db.sql("""
#         SELECT 
#             name, customer, grand_total, outstanding_amount, posting_time, paid_amount, posting_date, owner AS created_by
#         FROM `tabSales Invoice`
#         WHERE docstatus = 1 AND owner=%s AND posting_date BETWEEN %s AND %s
#     """, (user_email, from_date, to_date), as_dict=True)

#     # Sales Invoice Payments
#     sales_invoice_payments = frappe.db.sql("""
#         SELECT sip.mode_of_payment, SUM(sip.amount) as total_amount
#         FROM `tabSales Invoice Payment` sip
#         JOIN `tabSales Invoice` si ON si.name = sip.parent
#         WHERE si.docstatus = 1 AND si.owner = %s AND si.posting_date BETWEEN %s AND %s
#         GROUP BY sip.mode_of_payment
#     """, (user_email, from_date, to_date), as_dict=True)

#     # Update accounts summary with sales invoice payment details
#     for sip in sales_invoice_payments:
#         accounts_summary.setdefault(sip["mode_of_payment"], 0)
#         accounts_summary[sip["mode_of_payment"]] += sip["total_amount"]

#     for inv in sales_invoices:
#         inv["collected_amount"] = inv["paid_amount"] if inv["paid_amount"] is not None else inv["grand_total"] - inv["outstanding_amount"]

#     total_sales_amount = sum(inv["grand_total"] for inv in sales_invoices)
#     total_sales_amount_outstanding = sum(inv["outstanding_amount"] for inv in sales_invoices)
#     total_collected_amount = sum(inv["collected_amount"] for inv in sales_invoices)
#     grand_recived_amount = total_received_amount + total_collected_amount

#     # Purchase Invoices created by this user (only submitted)
#     purchase_invoices = frappe.db.sql("""
#         SELECT 
#             name, supplier, grand_total, outstanding_amount, paid_amount, posting_date, owner AS created_by
#         FROM `tabPurchase Invoice`
#         WHERE docstatus = 1 AND owner=%s AND posting_date BETWEEN %s AND %s
#     """, (user_email, from_date, to_date), as_dict=True)

#     for pinv in purchase_invoices:
#         pinv["paid_value"] = pinv["paid_amount"] if pinv["paid_amount"] is not None else pinv["grand_total"] - pinv["outstanding_amount"]

#     total_purchase_amount = sum(pinv["grand_total"] for pinv in purchase_invoices)
#     total_paid_purchase_amount = sum(pinv["paid_value"] for pinv in purchase_invoices)

#     data["received_payments"] = received_payments
#     data["paid_payments"] = paid_payments
#     data["internal_transfers"] = internal_transfers
#     data["sales_invoices"] = sales_invoices
#     data["purchase_invoices"] = purchase_invoices
#     data["accounts_summary"] = accounts_summary
#     data["expense_summary"] = expense_summary

#     totals = {
#         "total_received_payments": total_received_amount,
#         "total_paid_amount_tosupliers": total_paid_amount,
#         "total_internal_transfer_amount": total_internal_transfer_amount,
#         "total_sales_amount": total_sales_amount,
#         "total_sales_amount_outstanding": total_sales_amount_outstanding,
#         "grand_recived_amount": grand_recived_amount,
#         "total_collected_amount_sales": total_collected_amount,
#         "total_purchase_amount": total_purchase_amount,
#         "total_paid_purchase_amount": total_paid_purchase_amount
#     }

#     return {
#         "user": user_email,
#         "from_date": from_date,
#         "to_date": to_date,
#         "data": data,
#         "totals": totals
#     }

import frappe
from frappe import _

@frappe.whitelist()
def get_user_financial_totals(user_email, from_date, to_date):
    data = {}
    expense_summary = {}

    # Branch Expenses created by this user (only submitted)
    branch_expenses = frappe.db.sql("""
        SELECT 
            name, mode_of_payment, grand_total, date, owner AS created_by
        FROM `tabBranch Expenses`
        WHERE docstatus = 1 AND owner=%s AND date BETWEEN %s AND %s
    """, (user_email, from_date, to_date), as_dict=True)

    # Expense Claim Items Summary
    expense_claim_items = frappe.db.sql("""
        SELECT 
            sip.claim_type, SUM(sip.amount) AS total_amount
        FROM `tabExpense Claim Items` sip
        JOIN `tabBranch Expenses` si ON si.name = sip.parent
        WHERE si.docstatus = 1 AND si.owner=%s AND si.date BETWEEN %s AND %s
        GROUP BY sip.claim_type
    """, (user_email, from_date, to_date), as_dict=True)

    # Populate expense summary
    for item in expense_claim_items:
        claim_type = item["claim_type"]
        expense_summary[claim_type] = expense_summary.get(claim_type, 0) + item["total_amount"]

    # Payment Entries grouped by type and mode/account
    payment_entries = frappe.db.sql("""
        SELECT 
            name, party, paid_amount, payment_type, mode_of_payment, paid_from, paid_to, posting_date, owner AS created_by
        FROM `tabPayment Entry`
        WHERE docstatus = 1 AND owner=%s AND posting_date BETWEEN %s AND %s
    """, (user_email, from_date, to_date), as_dict=True)

    received_payments = [p for p in payment_entries if p["payment_type"] == "Receive"]
    paid_payments = [p for p in payment_entries if p["payment_type"] == "Pay"]
    internal_transfers = [p for p in payment_entries if p["payment_type"] == "Internal Transfer"]

    total_received_amount = sum(p["paid_amount"] for p in received_payments)
    total_paid_amount = sum(p["paid_amount"] for p in paid_payments)
    total_internal_transfer_amount = sum(p["paid_amount"] for p in internal_transfers)

    # Accounts summary from payment entries
    accounts_summary = {}
    for pe in payment_entries:
        if pe["payment_type"] in ["Receive", "Pay"]:
            account = pe["mode_of_payment"]
        elif pe["payment_type"] == "Internal Transfer":
            account = f"{pe['mode_of_payment']} ➝ {pe['paid_to']}"
        else:
            account = "Unknown"

        accounts_summary[account] = accounts_summary.get(account, 0) + pe["paid_amount"]

    # Sales Invoices created by this user (only submitted)
    sales_invoices = frappe.db.sql("""
        SELECT 
            name, customer, grand_total, outstanding_amount, paid_amount, posting_date, posting_time, owner AS created_by
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND owner=%s AND posting_date BETWEEN %s AND %s
    """, (user_email, from_date, to_date), as_dict=True)

    # Sales Invoice Payments summary
    sales_invoice_payments = frappe.db.sql("""
        SELECT 
            sip.mode_of_payment, SUM(sip.amount) AS total_amount
        FROM `tabSales Invoice Payment` sip
        JOIN `tabSales Invoice` si ON si.name = sip.parent
        WHERE si.docstatus = 1 AND si.owner=%s AND si.posting_date BETWEEN %s AND %s
        GROUP BY sip.mode_of_payment
    """, (user_email, from_date, to_date), as_dict=True)

    # Add sales payments to accounts summary
    for sip in sales_invoice_payments:
        mop = sip["mode_of_payment"]
        accounts_summary[mop] = accounts_summary.get(mop, 0) + sip["total_amount"]

    # Add collected amounts to sales invoices
    for inv in sales_invoices:
        paid_amount = inv.get("paid_amount") or (inv["grand_total"] - inv["outstanding_amount"])
        inv["collected_amount"] = paid_amount

    total_sales_amount = sum(inv["grand_total"] for inv in sales_invoices)
    total_sales_outstanding = sum(inv["outstanding_amount"] for inv in sales_invoices)
    total_collected_sales = sum(inv["collected_amount"] for inv in sales_invoices)
    grand_received_amount = total_received_amount + total_collected_sales

    # Purchase Invoices created by this user (only submitted)
    purchase_invoices = frappe.db.sql("""
        SELECT 
            name, supplier, grand_total, outstanding_amount, paid_amount, posting_date, owner AS created_by
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1 AND owner=%s AND posting_date BETWEEN %s AND %s
    """, (user_email, from_date, to_date), as_dict=True)

    for pinv in purchase_invoices:
        paid_value = pinv.get("paid_amount") or (pinv["grand_total"] - pinv["outstanding_amount"])
        pinv["paid_value"] = paid_value

    total_purchase_amount = sum(pinv["grand_total"] for pinv in purchase_invoices)
    total_paid_purchase_amount = sum(pinv["paid_value"] for pinv in purchase_invoices)

    # Pack data to return
    data.update({
        "branch_expenses": branch_expenses,
        "received_payments": received_payments,
        "paid_payments": paid_payments,
        "internal_transfers": internal_transfers,
        "sales_invoices": sales_invoices,
        "purchase_invoices": purchase_invoices,
        "accounts_summary": accounts_summary,
        "expense_summary": expense_summary
    })

    totals = {
        "total_received_payments": total_received_amount,
        "total_paid_amount_to_suppliers": total_paid_amount,
        "total_internal_transfer_amount": total_internal_transfer_amount,
        "total_sales_amount": total_sales_amount,
        "total_sales_outstanding": total_sales_outstanding,
        "total_collected_sales_amount": total_collected_sales,
        "grand_received_amount": grand_received_amount,
        "total_purchase_amount": total_purchase_amount,
        "total_paid_purchase_amount": total_paid_purchase_amount
    }

    return {
        "user": user_email,
        "from_date": from_date,
        "to_date": to_date,
        "data": data,
        "totals": totals
    }
