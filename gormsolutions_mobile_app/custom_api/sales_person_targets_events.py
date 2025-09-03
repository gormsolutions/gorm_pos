import frappe

def update_targets_on_invoice(doc, method):
	"""Update SalesPersonTargets only for the user of this Sales Invoice / Payment"""

	user = doc.owner
	company = getattr(doc, "company", None)

	# Find active Sales Person Targets for this user (and company if available)
	filters = {"dissable": 0, "user": user}
	if company:
		filters["company"] = company

	targets = frappe.get_all(
		"Sales Person Targets",
		filters=filters,
		fields=["name", "user", "company"]
	)

	if not targets:
		return

	# Recalculate outstanding from Sales Invoice table directly
	query = """
		SELECT SUM(outstanding_amount) as total
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		  AND owner = %s
	"""
	params = [user]

	if company:
		query += " AND company = %s"
		params.append(company)

	total_outstanding = frappe.db.sql(query, tuple(params))[0][0] or 0

	# Update only this user's targets
	for t in targets:
		frappe.db.set_value("Sales Person Targets", t.name, "credit_amount", total_outstanding)


import frappe
from frappe import _

def validate_credit_limit(doc, method):
	"""Block Sales Invoice if credit limit is exceeded for the owner (user)"""

	user = doc.owner
	company = doc.company

	# Get active Sales Person Target for this user & company
	target = frappe.get_value(
		"Sales Person Targets",
		{"user": user, "company": company, "dissable": 0},
		["name", "credit_limit", "credit_amount"],
		as_dict=True
	)

	if not target:
		return  # no target configured for this user, allow normally

	credit_limit = target.credit_limit or 0
	current_credit = target.credit_amount or 0
	new_invoice_outstanding = doc.outstanding_amount or doc.grand_total

	# Check if limit exceeded
	if credit_limit > 0 and (current_credit + new_invoice_outstanding) > credit_limit:
		frappe.throw(
			_("Credit limit exceeded for {0}! Current: {1}, New Invoice: {2}").format(
				user, current_credit, new_invoice_outstanding
			)
		)


@frappe.whitelist()
def fetch_credit_limit():
	"""
	Fetch Sales Person Targets (name, credit_limit, credit_amount)
	for the currently logged-in user and their company.
	"""

	current_user = frappe.session.user

	targets = frappe.get_all(
		"Sales Person Targets",
		filters={
			"user": current_user,
			"dissable": 0
		},
		fields=["name", "user", "credit_limit", "credit_amount"]
	)

	return targets
