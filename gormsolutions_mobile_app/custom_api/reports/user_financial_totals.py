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
	# payment_entries = frappe.db.sql("""
	#     SELECT 
	#         name, party, paid_amount, payment_type, mode_of_payment, paid_from, paid_to, posting_date, owner AS created_by
	#     FROM `tabPayment Entry`
	#     WHERE docstatus = 1 AND owner=%s AND posting_date BETWEEN %s AND %s
	# """, (user_email, from_date, to_date), as_dict=True)

	# received_payments = [p for p in payment_entries if p["payment_type"] == "Receive"]
	# paid_payments = [p for p in payment_entries if p["payment_type"] == "Pay"]
	# internal_transfers = [p for p in payment_entries if p["payment_type"] == "Internal Transfer"]

	# total_received_amount = sum(p["paid_amount"] for p in received_payments)
	# total_paid_amount = sum(p["paid_amount"] for p in paid_payments)
	# total_internal_transfer_amount = sum(p["paid_amount"] for p in internal_transfers)
	# Payment Entries grouped by type and mode/account (excluding only Sales Invoice links)
	payment_entries = frappe.db.sql("""
		SELECT 
			pe.name,
			pe.party,
			pe.paid_amount,
			pe.payment_type,
			pe.mode_of_payment,
			pe.paid_from,
			pe.paid_to,
			pe.posting_date,
			pe.owner AS created_by
		FROM `tabPayment Entry` pe
		WHERE 
			pe.docstatus = 1
			AND pe.owner = %s
			AND pe.posting_date BETWEEN %s AND %s
			AND NOT EXISTS (
				SELECT 1 
				FROM `tabPayment Entry Reference` per
				WHERE per.parent = pe.name
				AND per.reference_doctype = 'Sales Invoice'
			)
	""", (user_email, from_date, to_date), as_dict=True)

	# Group by payment type
	received_payments = [p for p in payment_entries if p["payment_type"] == "Receive"]
	paid_payments = [p for p in payment_entries if p["payment_type"] == "Pay"]
	internal_transfers = [p for p in payment_entries if p["payment_type"] == "Internal Transfer"]

	# Calculate totals
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
			name, customer, rounded_total, outstanding_amount, loyalty_amount,paid_amount, posting_date, posting_time, owner AS created_by
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
		paid_amount = inv.get("paid_amount") or (inv["rounded_total"] - inv["outstanding_amount"])
		inv["collected_amount"] = paid_amount

	total_sales_amount = sum(inv["rounded_total"] for inv in sales_invoices)
	total_loyalty_amount = sum(inv["loyalty_amount"] for inv in sales_invoices)
	total_sales_outstanding = sum(inv["outstanding_amount"] for inv in sales_invoices)
	total_collected_sales = sum(inv["collected_amount"] for inv in sales_invoices)
	grand_received_amount = (total_received_amount + total_collected_sales) - total_loyalty_amount

	# Purchase Invoices created by this user (only submitted)
	purchase_invoices = frappe.db.sql("""
		SELECT 
			name, supplier, rounded_total, outstanding_amount, paid_amount, posting_date, owner AS created_by
		FROM `tabPurchase Invoice`
		WHERE docstatus = 1 AND owner=%s AND posting_date BETWEEN %s AND %s
	""", (user_email, from_date, to_date), as_dict=True)

	for pinv in purchase_invoices:
		paid_value = pinv.get("paid_amount") or (pinv["rounded_total"] - pinv["outstanding_amount"])
		pinv["paid_value"] = paid_value

	total_purchase_amount = sum(pinv["rounded_total"] for pinv in purchase_invoices)
	total_paid_purchase_amount = sum(pinv["paid_value"] for pinv in purchase_invoices)
	grand_paid_purchase_amount = total_paid_purchase_amount + total_paid_amount

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
		"total_loyalty_amount": total_loyalty_amount,
		"total_sales_outstanding": total_sales_outstanding,
		"total_collected_sales_amount": total_collected_sales,
		"grand_received_amount": grand_received_amount,
		"total_purchase_amount": total_purchase_amount,
		"grand_paid_purchase_amount": grand_paid_purchase_amount,
		"total_paid_purchase_amount": total_paid_purchase_amount
	}

	return {
		"user": user_email,
		"from_date": from_date,
		"to_date": to_date,
		"data": data,
		"totals": totals
	}
