
import frappe
from frappe import _
from frappe.utils import cint


def validate_user_stock_transfer(doc, method):
	# ✅ Restrict only Material Transfer entries
	if doc.stock_entry_type != "Material Transfer":
		return

	user = frappe.session.user

	# ✅ Only enforce restrictions if the user has the "Transfer Permit" role
	if "Transfer Permit" not in frappe.get_roles(user):
		return

	# 🔹 Get all warehouses marked as default for this user
	default_warehouses = frappe.get_all(
		"Permitted Warehouse Items",
		filters={
			"parent": ["in", frappe.get_all(
				"Transfer Permitted Warehouse",
				filters={"user": user},
				pluck="name"
			)],
			"default": 1
		},
		fields=["warehouse"]
	)

	if not default_warehouses:
		return

	# Convert to a list for easier comparison
	default_warehouse_list = [w.warehouse for w in default_warehouses]

	for item in doc.items:
		source_warehouse = item.s_warehouse

		if source_warehouse not in default_warehouse_list:
			# 🔹 Find users permitted for this warehouse
			permitted_users = frappe.get_all(
				"Permitted Warehouse Items",
				filters={"warehouse": source_warehouse, "default": 1},
				fields=["parent"]
			)

			# Get corresponding usernames from Transfer Permitted Warehouse
			permitted_usernames = []
			for pu in permitted_users:
				username = frappe.db.get_value("Transfer Permitted Warehouse", pu.parent, "user")
				if username:
					permitted_usernames.append(username)

			# Fetch full names
			full_names = []
			for username in permitted_usernames:
				full_name = frappe.db.get_value("User", username, "full_name")
				if full_name:
					full_names.append(full_name)

			contact_info = ", ".join(full_names) if full_names else _("No user found")

			frappe.throw(_(
				f"You are not allowed to update this stock transfer.<br>"
				f"<b>Click Active button to reject with the reason</b><br>"
				f"Please contact the permitted user(s): <b>{contact_info}</b>."
			), title=_("Warehouse Restriction"))


def validate_user_stock_transfer_source_warehouse(doc, method):
	# ✅ Only validate Material Transfers
	if doc.stock_entry_type != "Material Transfer":
		return

	user = frappe.session.user

	# ✅ Only enforce restrictions if user has the "Transfer Permit" role
	if "Transfer Permit" not in frappe.get_roles(user):
		return

	# ✅ Require approval before proceeding
	# ✅ Require approval before proceeding (except Administrator)
	if (
		doc.custom_approve_status != "Approved"
		and frappe.session.user != "Administrator"
	):
		frappe.throw("Please approve the Stock Transfer before proceeding.")


	# 🔹 Get all warehouses marked as default for this user
	parent_records = frappe.get_all(
		"Transfer Permitted Warehouse",
		filters={"user": user},
		pluck="name"
	)

	default_warehouses = frappe.get_all(
		"Permitted Warehouse Items",
		filters={
			"parent": ["in", parent_records],
			"default": 1
		},
		fields=["warehouse"]
	)

	if not default_warehouses:
		return

	# Convert to a list for easier checking
	default_warehouse_list = [w.warehouse for w in default_warehouses]

	for item in doc.items:
		source_warehouse = item.s_warehouse
		target_warehouse = item.t_warehouse

		# ✅ Allow submission if target is default OR both source & target are defaults
		if target_warehouse in default_warehouse_list or (
			source_warehouse in default_warehouse_list and target_warehouse in default_warehouse_list
		):
			continue  # Allow submission, skip blocking

		# ❌ Otherwise, block submission
		permitted_records = frappe.get_all(
			"Permitted Warehouse Items",
			filters={
				"warehouse": source_warehouse,
				"parent": ["in", frappe.get_all(
					"Transfer Permitted Warehouse",
					filters={"user": ["!=", user]},
					pluck="name"
				)]
			},
			fields=["parent"]
		)

		# 🔹 Map parent back to users
		other_users = []
		for record in permitted_records:
			username = frappe.db.get_value(
				"Transfer Permitted Warehouse", record.parent, "user"
			)
			if username:
				other_users.append(username)

		# 🔹 Get full names of these users
		full_names = []
		for username in other_users:
			full_name = frappe.db.get_value("User", username, "full_name")
			if full_name:
				full_names.append(full_name)

		contact_info = ", ".join(full_names) if full_names else _("No other permitted users found.")

		frappe.throw(_(
			f"You are not allowed to submit this stock transfer.<br>"
			f"Contact permitted users for this warehouse: <b>{contact_info}</b>."
		), title=_("Warehouse Restriction"))

@frappe.whitelist()
def reject_stock_entry(docname, reason):
	if not docname or not reason:
		frappe.throw(_("Missing parameters."))

	frappe.db.sql("""
		UPDATE `tabStock Entry`
		SET custom_approve_status = %s,
			custom_reason = %s
		WHERE name = %s
	""", ("Rejected", reason, docname))
	frappe.db.commit()


@frappe.whitelist()
def approve_stock_entry(docname, accepted_qtys=None):
	if not docname:
		frappe.throw(_("Missing document name."))

	if isinstance(accepted_qtys, str):
		import json
		accepted_qtys = json.loads(accepted_qtys)

	# Update approval status
	frappe.db.sql("""
		UPDATE `tabStock Entry`
		SET custom_approve_status = %s,
			custom_reason = NULL
		WHERE name = %s
	""", ("Approved", docname))

	# Update child table values
	if accepted_qtys:
		for detail_name, accepted_qty in accepted_qtys.items():
			original_qty = frappe.db.get_value("Stock Entry Detail", detail_name, "qty") or 0
			custom_difference_qty = float(original_qty) - float(accepted_qty)

			frappe.db.sql("""
				UPDATE `tabStock Entry Detail`
				SET 
					qty = %s,
					custom_accepted_qty = %s,
					custom_difference_qty = %s,
					custom_original_qty = %s
				WHERE name = %s
			""", (accepted_qty, accepted_qty, custom_difference_qty, original_qty, detail_name))

	frappe.db.commit()


def validate_before_submit(doc, method):
	if doc.custom_approve_status == "Rejected":
		frappe.throw("You cannot submit a rejected Stock Entry.")

def create_material_issue_on_difference(doc, method):
	if doc.stock_entry_type == "Material Transfer":
		difference_items = []

		for d in doc.items:
			if d.custom_difference_qty and d.custom_difference_qty > 0:
				difference_items.append(d)

		if difference_items:
			# Get owner's full name and email
			user = frappe.get_doc("User", doc.owner)
			full_name = user.full_name
			user_email = user.name

			# Create Material Issue for shortage
			material_issue = frappe.new_doc("Stock Entry")
			material_issue.stock_entry_type = "Material Issue"
			material_issue.company = doc.company
			material_issue.posting_date = doc.posting_date
			material_issue.posting_time = doc.posting_time
			material_issue.custom_user_name = full_name
			material_issue.custom_user = user_email
			material_issue.set_stock_entry_type()

			# Determine correct expense account based on company
			if doc.company == "DIVA CAKES":
				expense_account = "1162013 - Employee Inventory Shortage - DC"
			elif doc.company == "CRAVE CITY MEGA LIMITED":
				expense_account = "1162013 - Employee Inventory Shortage - CCML"
			else:
				expense_account = "1162013 - Employee Inventory Shortage - DC"  # fallback/default

			for item in difference_items:
				material_issue.append("items", {
					"item_code": item.item_code,
					"qty": item.custom_difference_qty,
					"uom": item.uom,
					"stock_uom": item.stock_uom,
					"s_warehouse": item.s_warehouse,
					"expense_account": expense_account,
					"cost_center": item.cost_center
				})

			material_issue.insert(ignore_permissions=True)
			material_issue.submit()
			frappe.msgprint(
				_("Material Issue {0} created due to shortage.").format(material_issue.name)
			)


@frappe.whitelist()
def get_user_default_warehouse():
	"""
	Get all default warehouses for the logged-in user
	from Transfer Permitted Warehouse (parent) and
	Permitted Warehouse Items (child).
	"""
	user = frappe.session.user

	# 🔹 Find all Transfer Permitted Warehouse records for this user
	parent_records = frappe.get_all(
		"Transfer Permitted Warehouse",
		filters={"user": user},
		pluck="name"
	)

	if not parent_records:
		return None

	# 🔹 Get all warehouses marked as default in the child table
	default_warehouses = frappe.get_all(
		"Permitted Warehouse Items",
		filters={
			"parent": ["in", parent_records],
			"default": 1
		},
		fields=["warehouse"]
	)

	if not default_warehouses:
		return None

	# 🔹 Return a list if multiple defaults exist
	return [w.warehouse for w in default_warehouses]


def notify_permitted_users_on_save(doc, method):
	"""
	Send email notification to permitted warehouse users
	whenever a Material Transfer Stock Entry is saved,
	only if the user has 'Transfer Permit' role,
	and only once (tracked via custom_sent_email field).
	"""
	if doc.stock_entry_type != "Material Transfer":
		return

	user = frappe.session.user

	# ✅ Only enforce restrictions if the user has the "Transfer Permit" role
	if "Transfer Permit" not in frappe.get_roles(user):
		return

	# ✅ Do not send if already sent
	if doc.custom_sent_email == "Email Sent":
		return

	# Collect unique target warehouses from items
	target_warehouses = list({d.t_warehouse for d in doc.items if d.t_warehouse})

	if not target_warehouses:
		return

	permitted_emails = []
	permitted_names = []

	for target_warehouse in target_warehouses:
		permitted_users = frappe.get_all(
			"Permitted Warehouse Items",
			filters={"warehouse": target_warehouse, "default": 1},
			fields=["parent"]
		)

		for pu in permitted_users:
			username = frappe.db.get_value("Transfer Permitted Warehouse", pu.parent, "user")
			if username:
				email, full_name = frappe.db.get_value("User", username, ["email", "full_name"])
				if email and email not in permitted_emails:
					permitted_emails.append(email)
				if full_name and full_name not in permitted_names:
					permitted_names.append(full_name)

	# 📧 Send notification only if recipients found
	if permitted_emails:
		frappe.sendmail(
			recipients=permitted_emails,
			subject=_("Stock Transfer Notification"),
			message=_(
				f"Dear Approver,<br><br>"
				f"User <b>{frappe.utils.get_fullname(user)}</b> "
				f"saved a Stock Entry <b>{doc.name}</b> for transfer to "
				f"the following warehouses: <b>{', '.join(target_warehouses)}</b>.<br><br>"
				f"Please review if approval is required.<br><br>"
				f"Regards,<br>"
				f"ERP System"
			)
		)

		# ✅ Mark as sent silently (no modified timestamp change)
		frappe.db.set_value(
			"Stock Entry",
			doc.name,
			"custom_sent_email",
			"Email Sent",
			update_modified=False
		)
		# Also update the in-memory doc so UI shows the value
		doc.custom_sent_email = "Email Sent"
