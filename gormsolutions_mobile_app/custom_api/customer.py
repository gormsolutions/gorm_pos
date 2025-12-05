# import frappe
# from frappe import _
# from frappe.utils import today

# @frappe.whitelist(allow_guest=True)
# def get_customer_details(limit, offset, search=None):
#     try:
#         # Ensure limit and offset are integers
#         limit = int(limit)
#         offset = int(offset)

#         args = []
#         conditions = "disabled = 0 AND posa_referral_company = 'DIVA CAKES'"

#         if search:
#             search = search.strip()
#             like_search = f"%{search}%"
#             conditions += " AND (customer_name LIKE %s OR REPLACE(mobile_no, ' ', '') LIKE REPLACE(%s, ' ', ''))"
#             args += [like_search, like_search]

#         args += [limit, offset]

#         customer_list = frappe.db.sql(f"""
#             SELECT name, customer_name, mobile_no, email_id, creation
#             FROM `tabCustomer`
#             WHERE {conditions}
#             ORDER BY creation DESC
#             LIMIT %s OFFSET %s
#         """, args, as_dict=True)

#         result = []
#         for customer in customer_list:
#             summary = get_loyalty_summary_internal(customer.name)
#             customer.update(summary)
#             result.append(customer)

#         return result

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Get Customer Details Failed")
#         return {
#             "status": "error",
#             "message": _("Failed to retrieve customer list"),
#             "error": str(e)
#         }

import frappe # type: ignore
from frappe import _ # type: ignore
from frappe.utils import today # type: ignore

@frappe.whitelist(allow_guest=True)
def get_customer_details(limit, offset, search=None, last_sync=None):
	try:
		limit = int(limit)
		offset = int(offset)

		args = []
		conditions = "disabled = 0 AND posa_referral_company = 'DIVA CAKES' AND mobile_no IS NOT NULL AND mobile_no != ''"

		# If search is given
		if search:
			search = search.strip()
			like_search = f"%{search}%"
			conditions += " AND (customer_name LIKE %s OR REPLACE(mobile_no, ' ', '') LIKE REPLACE(%s, ' ', ''))"
			args += [like_search, like_search]

		# If last_sync is given
		if last_sync:
			conditions += " AND modified > %s"
			args.append(last_sync)

		# Add pagination args
		args += [limit, offset]

		# Main query
		customer_list = frappe.db.sql(f"""
			SELECT name, customer_name, mobile_no, email_id, creation, customer_group, modified
			FROM `tabCustomer`
			WHERE {conditions}
			ORDER BY modified DESC
			LIMIT %s OFFSET %s
		""", args, as_dict=True)

		# Add loyalty summary
		result = []
		for customer in customer_list:
			summary = get_loyalty_summary_internal(customer.name)
			customer.update(summary)
			result.append(customer)

		return result

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Customer Details Failed")
		return {
			"status": "error",
			"message": _("Failed to retrieve customer list"),
			"error": str(e)
		}

@frappe.whitelist(allow_guest=True)
def get_customer_details_crave(limit, offset, search=None, last_sync=None):
	try:
		limit = int(limit)
		offset = int(offset)

		args = []
		conditions = "disabled = 0 AND posa_referral_company = 'CRAVE CITY MEGA LIMITED' AND mobile_no IS NOT NULL AND mobile_no != ''"

		# If search is given
		if search:
			search = search.strip()
			like_search = f"%{search}%"
			conditions += " AND (customer_name LIKE %s OR REPLACE(mobile_no, ' ', '') LIKE REPLACE(%s, ' ', ''))"
			args += [like_search, like_search]

		# If last_sync is given
		if last_sync:
			conditions += " AND modified > %s"
			args.append(last_sync)

		# Add pagination args
		args += [limit, offset]

		# Main query
		customer_list = frappe.db.sql(f"""
			SELECT name, customer_name, mobile_no, email_id, creation, customer_group,modified
			FROM `tabCustomer`
			WHERE {conditions}
			ORDER BY modified DESC
			LIMIT %s OFFSET %s
		""", args, as_dict=True)

		# Add loyalty summary
		result = []
		for customer in customer_list:
			summary = get_loyalty_summary_internal(customer.name)
			customer.update(summary)
			result.append(customer)

		return result

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Customer Details Failed")
		return {
			"status": "error",
			"message": _("Failed to retrieve customer list"),
			"error": str(e)
		}


@frappe.whitelist(allow_guest=True)
def get_loyalty_summary_internal(customer):
	earned = 0
	redeemed = 0
	program = None

	entries = frappe.get_all(
		"Loyalty Point Entry",
		filters={
			"customer": customer,
			"expiry_date": [">=", frappe.utils.nowdate()]
		},
		fields=["loyalty_points", "loyalty_program"]
	)

	for entry in entries:
		points = entry.loyalty_points or 0

		if points > 0:
			earned += points
		elif points < 0:
			redeemed += points
		if not program and entry.loyalty_program:
			program = entry.loyalty_program

	remaining = earned + redeemed

	conversion_rate = 0
	redeemed_value = 0
	remaining_value = 0

	if program:
		loyalty_program = frappe.get_doc("Loyalty Program", program)
		conversion_rate = loyalty_program.conversion_factor or 0
		redeemed_value = abs(redeemed) * conversion_rate
		remaining_value = remaining * conversion_rate

	return {
		"loyalty_program": program,
		"earned_points": earned,
		"redeemed_points": abs(redeemed),
		"remaining_points": remaining,
		"conversion_rate": conversion_rate,
		"redeemed_value": redeemed_value,
		"remaining_value": remaining_value
	}

@frappe.whitelist(allow_guest=True)
def create_customer(
	customer_name,
	mobile_no,
	email_id=None,
	naming_series="CUST-.YYYY.-",
	customer_type="Individual",
	customer_group=None,
	territory=None
):
	try:
		current_user = frappe.session.user

		# --- Step 1: Check for existing customer with same mobile number ---
		existing = frappe.db.get_all(
			"Customer",
			filters={"mobile_no": mobile_no.strip()},
			fields=["name", "customer_name", "custom_cost_center"]
		)

		if existing:
			return {
				"status": "exists",
				"message": _("A customer with this mobile number already exists."),
				"customer": existing[0].name,
				"customer_name": existing[0].customer_name,
				"custom_cost_center": existing[0].custom_cost_center
			}

		# --- Step 2: Fetch POS Profile for user ---
		result = frappe.db.sql("""
			SELECT ppu.parent
			FROM `tabPOS Profile User` ppu
			JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
			WHERE ppu.user = %s AND ppu.default = 1 AND pp.disabled = 0
			LIMIT 1
		""", (current_user,), as_dict=0)

		if not result:
			return {
				"status": "error",
				"message": _("No default POS Profile found for user.")
			}

		pos_profile = result[0][0]

		# --- Step 3: Get Cost Center ---
		cost_center = frappe.db.get_value("POS Profile", pos_profile, "cost_center")
		if not cost_center:
			return {
				"status": "error",
				"message": _("No Cost Center configured in the POS Profile.")
			}

		# --- Step 4: Create Customer ---
		doc = frappe.new_doc('Customer')
		doc.naming_series = naming_series
		doc.customer_name = customer_name.strip()
		doc.mobile_no = mobile_no.strip()
		doc.customer_type = customer_type
		doc.customer_group = customer_group
		doc.custom_cost_center = cost_center
		doc.territory = territory

		if email_id:
			doc.email_id = email_id.strip()

		doc.insert(ignore_permissions=True)
		frappe.db.commit()

		return {
			"status": "success",
			"message": _("Customer created successfully"),
			"customer": doc.name,
			"customer_name": doc.customer_name,
			"custom_cost_center": cost_center
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Customer Creation Failed")
		return {
			"status": "error",
			"message": _("Failed to create customer"),
			"error": str(e)
		}

@frappe.whitelist()
def fetch_customer_metadata():
	try:
		# Fetch all Customer Groups
		customer_groups = frappe.get_all(
			"Customer Group",
			filters={"is_group": 0},
			fields=["name"]
		)

		# Fetch all Territories
		territories = frappe.get_all(
			"Territory",
			filters={"is_group": 0},
			fields=["name"]
		)

		return {
			"status": "success",
			"message": _("Customer metadata fetched successfully"),
			"data": {
				"customer_groups": [g.name for g in customer_groups],
				"territories": [t.name for t in territories]
			}
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Fetch Customer Metadata Failed")
		return {
			"status": "error",
			"message": _("Failed to fetch customer metadata"),
			"error": str(e)
		}

@frappe.whitelist(allow_guest=True)
def get_customer_count():
	try:
		total_count = frappe.db.count("Customer", filters={
			"disabled": 0,
			 "mobile_no": ["!=", ""],
			"posa_referral_company": "DIVA CAKES"
		})

		return {
			"total_count": total_count
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_customer_details error")
		return {"error": str(e)}

@frappe.whitelist()
def get_customer_groups():
	"""
	Returns all active Customer Groups.
	"""
	customer_groups = frappe.get_all(
		"Customer Group",
		fields=["name"],
		order_by="name asc"
	)

	return customer_groups

@frappe.whitelist(allow_guest=True)
def get_crave_customers_today(limit, offset, search=None):
	try:
		limit = int(limit)
		offset = int(offset)

		args = []
		conditions = """
			disabled = 0
			AND posa_referral_company = 'CRAVE CITY MEGA LIMITED'
			AND (DATE(creation) = CURDATE() OR DATE(modified) = CURDATE())
			AND mobile_no IS NOT NULL
			AND mobile_no != ''
		"""


		# Search filter
		if search:
			search = search.strip()
			like_search = f"%{search}%"
			conditions += """
				AND (
					customer_name LIKE %s
					OR REPLACE(mobile_no, ' ', '') LIKE REPLACE(%s, ' ', '')
				)
			"""
			args += [like_search, like_search]

		# Pagination
		args += [limit, offset]

		# Query
		customer_list = frappe.db.sql(f"""
			SELECT name, customer_name, mobile_no, email_id, creation,
				   customer_group, modified
			FROM `tabCustomer`
			WHERE {conditions}
			ORDER BY modified DESC
			LIMIT %s OFFSET %s
		""", args, as_dict=True)

		# Loyalty summary
		result = []
		for customer in customer_list:
			summary = get_loyalty_summary_internal(customer.name)
			customer.update(summary)
			result.append(customer)

		return result

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Customer Details Failed")
		return {
			"status": "error",
			"message": "Failed to retrieve customer list",
			"error": str(e)
		}

@frappe.whitelist(allow_guest=True)
def get_diva_customers_today(limit, offset, search=None):
	try:
		limit = int(limit)
		offset = int(offset)

		args = []
		conditions = """
			disabled = 0
			AND posa_referral_company = 'DIVA CAKES'
			AND (DATE(creation) = CURDATE() OR DATE(modified) = CURDATE())
			AND mobile_no IS NOT NULL
			AND mobile_no != ''
		"""

		# Search filter
		if search:
			search = search.strip()
			like_search = f"%{search}%"
			conditions += """
				AND (
					customer_name LIKE %s
					OR REPLACE(mobile_no, ' ', '') LIKE REPLACE(%s, ' ', '')
				)
			"""
			args += [like_search, like_search]

		# Pagination
		args += [limit, offset]

		# Main query
		customer_list = frappe.db.sql(f"""
			SELECT name, customer_name, mobile_no, email_id, creation,
				   customer_group, modified
			FROM `tabCustomer`
			WHERE {conditions}
			ORDER BY modified DESC
			LIMIT %s OFFSET %s
		""", args, as_dict=True)

		# Loyalty summary
		result = []
		for customer in customer_list:
			summary = get_loyalty_summary_internal(customer.name)
			customer.update(summary)
			result.append(customer)

		return result

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Today Customer Details (DIVA CAKES) Failed")
		return {
			"status": "error",
			"message": "Failed to retrieve customer list",
			"error": str(e)
		}


@frappe.whitelist(allow_guest=True)
def get_customer_count_crave():
	try:
		total_count = frappe.db.count("Customer", filters={
			"disabled": 0,
			 "mobile_no": ["!=", ""],
			"posa_referral_company": "CRAVE CITY MEGA LIMITED"
		})

		return {
			"total_count": total_count
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_customer_details error")
		return {"error": str(e)}
