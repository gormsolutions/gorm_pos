import frappe

def create_discount_journal_entry(doc, method):
    total_discount = 0
    discount_account = None

    # Sum discount from item table
    for item in doc.items:
        if (item.discount_amount or item.discount_percentage) and item.discount_account:
            if item.discount_amount > 0:
                amount = item.discount_amount
            else:
                # calculate percentage discount
                amount = (item.rate * item.qty) * (item.discount_percentage / 100)

            total_discount += amount
            discount_account = item.discount_account  # pick last entered account

    # If no discount, exit
    if not total_discount or not discount_account:
        return

    # Create Journal Entry
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = doc.posting_date
    je.user_remark = f"Discount for Sales Invoice {doc.name}"
    je.company = doc.company

    # Debit Discount Allowed account
    je.append("accounts", {
        "account": discount_account,
        "debit_in_account_currency": total_discount,
        "credit_in_account_currency": 0,
        "cost_center": doc.cost_center
    })

    # Credit Customer (reduce receivable)
    je.append("accounts", {
        "account": doc.debit_to,
        "party_type": "Customer",
        "party": doc.customer,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": total_discount,
        "cost_center": doc.cost_center
    })

    je.insert(ignore_permissions=True)
    je.submit()
