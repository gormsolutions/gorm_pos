import frappe
from frappe.utils import getdate, formatdate
from collections import defaultdict

@frappe.whitelist()
def get_expense_accounts_details(company=None, cost_center=None, from_date=None, to_date=None):
	"""
	Get only Expense Accounts (account_type = 'Expense Account', root_type = 'Expense')
	Grouped by account, separated by month.
	"""
	return _get_monthly_expense_details(company, cost_center, from_date, to_date,
										account_type_filter='Expense Account')


@frappe.whitelist()
def get_cogs_expense_details(company=None, cost_center=None, from_date=None, to_date=None):
	"""
	Get only COGS entries (account_type = 'Cost of Goods Sold', root_type = 'Expense')
	Grouped by account, separated by month.
	"""
	return _get_monthly_expense_details(company, cost_center, from_date, to_date,
										account_type_filter='Cost of Goods Sold')


def _get_monthly_expense_details(company, cost_center, from_date, to_date, account_type_filter):
	"""
	Internal helper function to fetch GL entries filtered by account_type.
	Populates items from all relevant child tables.
	"""
	conditions = [
		"gle.is_cancelled = 0",
		"gle.debit > 0",
		"acc.account_type = %(account_type)s",
		"acc.root_type = 'Expense'"
	]
	values = {"account_type": account_type_filter}

	if company:
		conditions.append("gle.company = %(company)s")
		values["company"] = company

	if cost_center:
		conditions.append("gle.cost_center = %(cost_center)s")
		values["cost_center"] = cost_center

	if from_date:
		conditions.append("gle.posting_date >= %(from_date)s")
		values["from_date"] = getdate(from_date)

	if to_date:
		conditions.append("gle.posting_date <= %(to_date)s")
		values["to_date"] = getdate(to_date)

	condition_sql = " AND ".join(conditions)

	# Fetch GL entries
	gl_entries = frappe.db.sql(f"""
		SELECT
			DATE_FORMAT(gle.posting_date, '%%Y-%%m') AS month,
			gle.posting_date,
			gle.account,
			acc.account_type,
			acc.root_type,
			gle.cost_center,
			gle.debit AS expense_amount,
			gle.remarks,
			gle.voucher_type,
			gle.voucher_no,
			gle.against,
			gle.party_type,
			gle.party
		FROM `tabGL Entry` gle
		LEFT JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {condition_sql}
		ORDER BY gle.posting_date ASC
	""", values, as_dict=True)

	# Attach items for all voucher types
	for row in gl_entries:
		row["items"] = []

		if row["voucher_type"] == "Purchase Invoice":
			row["items"] = frappe.db.sql("""
				SELECT item_code, item_name, description, qty, base_net_amount AS amount
				FROM `tabPurchase Invoice Item`
				WHERE parent = %s
			""", (row["voucher_no"]), as_dict=True)

		elif row["voucher_type"] == "Expense Claim":
			row["items"] = frappe.db.sql("""
				SELECT expense_type AS item_code, description, amount
				FROM `tabExpense Claim Detail`
				WHERE parent = %s
			""", (row["voucher_no"]), as_dict=True)

		elif row["voucher_type"] == "Purchase Receipt":
			row["items"] = frappe.db.sql("""
				SELECT item_code, item_name, description, qty, base_net_amount AS amount
				FROM `tabPurchase Receipt Item`
				WHERE parent = %s
			""", (row["voucher_no"]), as_dict=True)

		elif row["voucher_type"] == "Journal Entry":
			row["items"] = frappe.db.sql("""
				SELECT account AS item_code, cost_center, debit AS amount,credit,IFNULL(party_type, '') AS party_type,
				IFNULL(party, '') AS party
				FROM `tabJournal Entry Account`
				WHERE parent = %s
			""", (row["voucher_no"]), as_dict=True)
		
		elif row["voucher_type"] == "Sales Invoice":
			# Pull sold items
			items = frappe.db.sql("""
				SELECT item_code, item_name, qty, base_net_amount AS selling_amount
				FROM `tabSales Invoice Item`
				WHERE parent = %s
			""", (row["voucher_no"]), as_dict=True)

			# Map cost per item from Stock Ledger / Item Valuation
			for item in items:
				item_val = frappe.db.sql("""
					SELECT valuation_rate
					FROM `tabStock Ledger Entry`
					WHERE voucher_no = %s AND item_code = %s
					ORDER BY posting_date ASC LIMIT 1
				""", (row["voucher_no"], item["item_code"]), as_dict=True)
				item["cost_amount"] = item_val[0]["valuation_rate"] * item["qty"] if item_val else 0.0

			row["items"] = items



		elif row["voucher_type"] == "Payment Entry":
			row["items"] = frappe.db.sql("""
				SELECT reference_type AS item_code, reference_name AS voucher, allocated_amount AS amount
				FROM `tabPayment Entry Reference`
				WHERE parent = %s
			""", (row["voucher_no"]), as_dict=True)

	# Organize by month and account
	results = {}
	for row in gl_entries:
		month_key = row["month"]
		if month_key not in results:
			results[month_key] = {
				"month": formatdate(month_key + "-01", "MMM YYYY"),
				"total": 0.0,
				"by_account": defaultdict(lambda: {"total": 0.0, "entries": []}),
			}
		results[month_key]["total"] += row["expense_amount"]
		results[month_key]["by_account"][row["account"]]["total"] += row["expense_amount"]
		results[month_key]["by_account"][row["account"]]["entries"].append(row)

	# Convert defaultdict → dict
	final = []
	for month_key, data in results.items():
		data["by_account"] = dict(data["by_account"])
		final.append(data)

	final = sorted(final, key=lambda x: x["month"])
	return final
