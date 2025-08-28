import frappe
from frappe import _
from frappe.utils import cint

def validate_user_stock_transfer(doc, method):
	if doc.purpose != "Material Transfer":
		return

	user = frappe.session.user

	# Only enforce if the user has the "Transfer Permit" role
	if "Transfer Permit" not in frappe.get_roles(user):
		return

	# Get the user's default warehouse
	default_perm = frappe.get_all(
		"User Permission",
		filters={
			"user": user,
			"allow": "Warehouse",
			"is_default": 1
		},
		fields=["for_value"],
		limit=1
	)

	if not default_perm:
		frappe.throw(_("No default warehouse found for your user permissions. Contact Administrator."))

	default_warehouse = default_perm[0].for_value

	for item in doc.items:
		source_warehouse = item.s_warehouse

		if source_warehouse != default_warehouse:
			# Find users permitted for this warehouse
			permitted_users = frappe.get_all(
				"User Permission",
				filters={
					"allow": "Warehouse",
					"for_value": source_warehouse,
					"is_default": 1
				},
				fields=["user"]
			)

			# Fetch full names
			full_names = []
			for pu in permitted_users:
				full_name = frappe.db.get_value("User", pu.user, "full_name")
				if full_name:
					full_names.append(full_name)

			contact_info = ", ".join(full_names) if full_names else _("No user found")

			frappe.throw(_(
				f"You are not allowed Update this stock transfer.<b>Click Active button to reject with the reason </b><br>"
				f"Please contact the permitted user(s): <b>{contact_info}</b> ."
			), title=_("Warehouse Restriction"))

# In gormsolutions_mobile_app/custom_api/stock/stock_transfer_setting.py
# File: gormsolutions_mobile_app/custom_api/stock/stock_transfer_setting.py


def validate_user_stock_transfer_source_warehouse(doc, method):
	if doc.purpose != "Material Transfer":
		return

	user = frappe.session.user

	if "Transfer Permit" not in frappe.get_roles(user):
		return
	
	if doc.custom_approve_status != "Approved":
		frappe.throw("Please Approve the Stock Transfer.")


	# Get user's default warehouse
	default_perm = frappe.get_all(
		"User Permission",
		filters={
			"user": user,
			"allow": "Warehouse",
			"is_default": 1
		},
		fields=["for_value"],
		limit=1
	)

	if not default_perm:
		frappe.throw(_("No default warehouse found for your user permissions. Contact Administrator."))


	default_warehouse = default_perm[0].for_value

	for item in doc.items:
		source_warehouse = item.s_warehouse

		# ❌ Restrict if user is trying to transfer from their default warehouse
		if source_warehouse == default_warehouse:
			# Find other permitted users for that warehouse
			permitted_users = frappe.get_all(
				"User Permission",
				filters={
					"allow": "Warehouse",
					"for_value": source_warehouse,
					"is_default": 0,
					"user": ["!=", user]  # exclude current user
				},
				fields=["user"]
			)

			# Get their full names
			full_names = []
			for pu in permitted_users:
				full_name = frappe.db.get_value("User", pu.user, "full_name")
				if full_name:
					full_names.append(full_name)

			contact_info = ", ".join(full_names) if full_names else _("No other permitted users found.")

			frappe.throw(_(
				f"You are not allowed to Submit this stock transfer.<br>"
				f"Contact Permitted users for this warehouse: <b>{contact_info}</b>."
			), title=_("Warehouse Restriction"))



@frappe.whitelist()
def reject_stock_entry(docname, reason):
	if not docname or not reason:
		frappe.throw(_("Missing parameters."))

	# Update fields directly in DB
	frappe.db.sql("""
		UPDATE `tabStock Entry`
		SET custom_approve_status = %s,
			custom_reason = %s
		WHERE name = %s
	""", ("Rejected", reason, docname))

	frappe.db.commit()
	

# @frappe.whitelist()
# def approve_stock_entry(docname):
#     if not docname:
#         frappe.throw(_("Missing document name."))

#     frappe.db.sql("""
#         UPDATE `tabStock Entry`
#         SET custom_approve_status = %s,
#             custom_reason = NULL
#         WHERE name = %s
#     """, ("Approved", docname))
#     frappe.db.commit()

@frappe.whitelist()
def approve_stock_entry(docname, accepted_qtys=None):
	if not docname:
		frappe.throw(_("Missing document name."))

	if isinstance(accepted_qtys, str):
		import json
		accepted_qtys = json.loads(accepted_qtys)

	# Update approval status directly in Stock Entry
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

import frappe

# def assign_transfer_permit_to_all_users():
#     role_name = "Transfer Permit"
	
#     # Get all active system users (not Guests or Website Users)
#     users = frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, pluck="name")
	
#     for user in users:
#         # Check if user already has the role
#         if not frappe.db.exists("Has Role", {"parent": user, "role": role_name}):
#             user_doc = frappe.get_doc("User", user)
#             user_doc.append("roles", {
#                 "role": role_name
#             })
#             user_doc.save(ignore_permissions=True)
#             frappe.db.commit()
#             print(f"Assigned '{role_name}' to {user}")

# # Call the function
# assign_transfer_permit_to_all_users()


# def set_pending_approval(doc, method):
#     if doc.purpose == "Material Transfer" and not doc.custom_approve_status:
#         doc.custom_approve_status = "Pending Approval"


# Hook this on_submit for Stock Entry DocType
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
			
			# Always use the company from the Stock Entry
			company = doc.company

			# Fetch company-specific shortage settings
			shortage_settings = frappe.get_value(
				"Stock Gormpos Settings",
				{"company": company},
				["name", "employee_shortage_account"],
				as_dict=True
			)

			if not shortage_settings:
				frappe.throw(_("Please configure Stock Gormpos Settings for company {0}.").format(company))

			if not shortage_settings.employee_shortage_account:
				frappe.throw(_("Please set Employee Shortage Account in Stock Gormpos Settings for company {0}.").format(company))


			# Create a new Material Issue
			material_issue = frappe.new_doc("Stock Entry")
			material_issue.stock_entry_type = "Material Issue"
			material_issue.company = doc.company
			material_issue.posting_date = doc.posting_date
			material_issue.posting_time = doc.posting_time
			material_issue.custom_user_name = full_name
			material_issue.custom_user = user_email
			material_issue.set_stock_entry_type()

			for item in difference_items:
				material_issue.append("items", {
					"item_code": item.item_code,
					"qty": item.custom_difference_qty,  # Set Qty from custom_difference_qty
					"uom": item.uom,
					"stock_uom": item.stock_uom,
					"s_warehouse": item.s_warehouse,
					"expense_account": shortage_settings.employee_shortage_account,
					"cost_center": item.cost_center
				})

			material_issue.insert(ignore_permissions=True)
			material_issue.submit()
			frappe.msgprint(_("Material Issue {0} created due to shortage.").format(material_issue.name))


@frappe.whitelist()
def get_user_default_warehouse():
	user = frappe.session.user
	default_perm = frappe.get_all(
		"User Permission",
		filters={
			"user": user,
			"allow": "Warehouse",
			"is_default": 1
		},
		fields=["for_value"],
		limit=1
	)

	if not default_perm:
		return None
	return default_perm[0].for_value
