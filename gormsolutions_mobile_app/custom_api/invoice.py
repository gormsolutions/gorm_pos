import frappe
import json
from frappe.utils import flt
from frappe import _

# @frappe.whitelist(allow_guest=True)
# def get_invoice_details(limit, offset, search=None):
# 	# Initialize filters with docstatus filter
# 	filters = [["docstatus", "=", 1]]

# 	# Add a filter for the logged-in user
# 	filters.append(["owner", "=", frappe.session.user])

# 	# If a search term is provided, add a filter for customer_name
# 	if search:
# 		filters.append(["customer_name", "like", f"%{search}%"])

# 	# Fetch filtered Sales Invoice details
# 	sales_invoice_details = frappe.get_all(
# 		'Sales Invoice',
# 		fields=[
# 			'name', 'grand_total', 'remarks', 'posting_date', 'paid_amount', 'outstanding_amount',
# 			'owner', 'docstatus', 'status', 'customer', 'customer_name'
# 		],
# 		order_by='posting_date desc',
# 		filters=filters,
# 		start=offset,
# 		page_length=limit
# 	)

# 	# Fetch and attach items and payment info
# 	for invoice in sales_invoice_details:
# 		invoice["items"] = frappe.get_all(
# 			"Sales Invoice Item",
# 			fields=["item_code", "item_name", "qty", "uom", "rate", "amount"],
# 			filters={"parent": invoice["name"]}
# 		)

# 		invoice["payments"] = frappe.get_all(
# 			"Sales Invoice Payment",
# 			fields=["mode_of_payment", "amount", "reference_no"],
# 			filters={"parent": invoice["name"]}
# 		)

# 	return sales_invoice_details


@frappe.whitelist(allow_guest=True)
def get_invoice_details(limit, offset, search=None, from_date=None, to_date=None):
	# Initialize filters with docstatus filter
	filters = [["docstatus", "=", 1]]

	# Add a filter for the logged-in user
	filters.append(["owner", "=", frappe.session.user])

	# If a search term is provided, add a filter for customer_name
	if search:
		filters.append(["customer_name", "like", f"%{search}%"])

	# Exact BETWEEN dates (inclusive)
	if from_date and to_date:
		filters.append(["posting_date", "between", [from_date, to_date]])

	# Fetch filtered Sales Invoice details
	sales_invoice_details = frappe.get_all(
		'Sales Invoice',
		fields=[
			'name', 'grand_total', 'remarks', 'posting_date', 'paid_amount', 'outstanding_amount',
			'owner', 'docstatus', 'status', 'customer', 'customer_name'
		],
		order_by='posting_date desc',
		filters=filters,
		start=offset,
		page_length=limit
	)

	# Fetch and attach items and payment info
	for invoice in sales_invoice_details:
		invoice["items"] = frappe.get_all(
			"Sales Invoice Item",
			fields=["item_code", "item_name", "qty", "uom", "rate", "amount"],
			filters={"parent": invoice["name"]}
		)

		invoice["payments"] = frappe.get_all(
			"Sales Invoice Payment",
			fields=["mode_of_payment", "amount", "reference_no"],
			filters={"parent": invoice["name"]}
		)

	return sales_invoice_details


@frappe.whitelist(allow_guest=True)
def get_invoice_details(limit, offset, search=None, from_date=None, to_date=None):
	# Initialize filters with docstatus filter
	filters = [["docstatus", "=", 1]]

	# Add a filter for the logged-in user
	filters.append(["owner", "=", frappe.session.user])

	# If a search term is provided, add a filter for customer_name
	if search:
		filters.append(["customer_name", "like", f"%{search}%"])

	# Optional date filters (posting_date)
	if from_date:
		filters.append(["posting_date", ">=", from_date])

	if to_date:
		filters.append(["posting_date", "<=", to_date])

	# Fetch filtered Sales Invoice details
	sales_invoice_details = frappe.get_all(
		'Sales Invoice',
		fields=[
			'name', 'grand_total', 'remarks', 'posting_date', 'paid_amount', 'outstanding_amount',
			'owner', 'docstatus', 'status', 'customer', 'customer_name'
		],
		order_by='posting_date desc',
		filters=filters,
		start=offset,
		page_length=limit
	)

	# Fetch and attach items and payment info
	for invoice in sales_invoice_details:
		invoice["items"] = frappe.get_all(
			"Sales Invoice Item",
			fields=["item_code", "item_name", "qty", "uom", "rate", "amount"],
			filters={"parent": invoice["name"]}
		)

		invoice["payments"] = frappe.get_all(
			"Sales Invoice Payment",
			fields=["mode_of_payment", "amount", "reference_no"],
			filters={"parent": invoice["name"]}
		)

	return sales_invoice_details


# @frappe.whitelist()
# def create_invoice(
# 	customer_name,
# 	paid_amount=None,
# 	items=None,
# 	remarks=None,
# 	payments=None,
# 	mode_of_payment=None,
# 	reference_no=None,
# 	user=None,
# 	is_pos=None,
# 	update_stock=None,
# 	discount_amount=0,
# 	discount_percentage=0,
# 	loyalty_points=None,
# 	redeem_loyalty_points=None
# ):
# 	current_user = user or frappe.session.user

# 	if not customer_name:
# 		return {"error": "Cannot create invoice: Customer not selected.", "status": "not_posted"}

# 	# --- Parse Inputs ---
# 	if isinstance(items, str):
# 		items = json.loads(items)
# 	if isinstance(payments, str):
# 		payments = json.loads(payments)

# 	# --- Get Warehouse ---
# 	fallback_warehouse = frappe.get_all(
# 		'User Permission',
# 		filters={'user': current_user, 'allow': 'Warehouse', "is_default": 0},
# 		fields=['for_value']
# 	)
# 	fallback_warehouse = fallback_warehouse[0]['for_value'] if fallback_warehouse else \
# 						 frappe.db.get_single_value('Stock Settings', 'default_warehouse')

# 	if not fallback_warehouse:
# 		return {"error": "No warehouse assigned to user and no default warehouse in Stock Settings."}

# 	# --- Get POS Profile if applicable ---
# 	pos_profile = pos_warehouse = fulfillment_branch = company = cost_center = None
# 	if is_pos:
# 		result = frappe.db.sql("""
# 			SELECT ppu.parent
# 			FROM `tabPOS Profile User` ppu
# 			JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
# 			WHERE ppu.user = %s AND ppu.default = 1 AND pp.disabled = 0
# 			LIMIT 1
# 		""", (current_user,), as_dict=0)

# 		if result:
# 			pos_profile = result[0][0]
# 			pos_warehouse = frappe.db.get_value("POS Profile", pos_profile, "warehouse")
# 			fulfillment_branch = frappe.db.get_value("POS Profile", pos_profile, "fulfillment_branch_")
# 			cost_center = frappe.db.get_value("POS Profile", pos_profile, "cost_center")
# 			company = frappe.db.get_value("POS Profile", pos_profile, "company")
# 		else:
# 			return {"error": f"No enabled default POS Profile found for user '{current_user}'."}

# 	# --- Assign Warehouse and Cost Center to Items ---
# 	if is_pos or update_stock:
# 		for item in items or []:
# 			item["warehouse"] = pos_warehouse or fallback_warehouse
# 			item["cost_center"] = cost_center
# 		update_stock = 1

# 	# --- Payment Entries ---
# 	payment_entries = []
# 	if payments:
# 		for p in payments:
# 			mode = p.get("mode_of_payment")
# 			amount = flt(p.get("amount") or 0)
# 			reference = p.get("reference_no")
# 			if amount > 0:
# 				payment_entries.append({
# 					"mode_of_payment": mode,
# 					"amount": amount,
# 					"reference_no": reference
# 				})
# 	elif mode_of_payment and paid_amount:
# 		payment_entries.append({
# 			"mode_of_payment": mode_of_payment,
# 			"amount": flt(paid_amount),
# 			"reference_no": reference_no
# 		})

# 	# --- Duplicate Prevention ---
# 	# Use remarks as unique UID (from offline)
# 	if remarks:
# 		existing_invoice = frappe.db.exists(
# 			"Sales Invoice",
# 			{"remarks": remarks}
# 		)
# 		if existing_invoice:
# 			return {"error": f"Duplicate entry: Invoice with UID '{remarks}' already exists ({existing_invoice})."}

# 	# Also block if same reference_no already linked to a payment
# 	if reference_no:
# 		ref_exists = frappe.db.exists(
# 			"Sales Invoice Payment",
# 			{"reference_no": reference_no}
# 		)
# 		if ref_exists:
# 			return {"error": f"Duplicate payment reference: {reference_no} already used ({ref_exists})."}

# 	# --- Prepare Invoice Data ---
# 	invoice_doc_data = {
# 		"doctype": "Sales Invoice",
# 		"customer": customer_name,
# 		"company": company,
# 		"remarks": remarks,  # <-- your unique UID
# 		"custom_from": "GormPos",
# 		"fulfillment_branch_": fulfillment_branch,
# 		"cost_center": cost_center,
# 		"update_stock": update_stock,
# 		"confirm_branch": 1,
# 		"is_pos": is_pos,
# 		"items": items or [],
# 		"discount_amount": discount_amount,
# 		"additional_discount_percentage": discount_percentage,
# 		"apply_discount_on": "Grand Total",
# 		"payments": payment_entries,
# 		"redeem_loyalty_points": redeem_loyalty_points,
# 		"loyalty_points": flt(loyalty_points),
# 	}

# 	if is_pos:
# 		invoice_doc_data["pos_profile"] = pos_profile

# 	# --- Insert and Submit ---
# 	try:
# 		invoice_doc = frappe.get_doc(invoice_doc_data)

# 		# Safety: check again before final insert (in case of race condition)
# 		if frappe.db.exists("Sales Invoice", {"remarks": remarks}):
# 			return {"error": f"Duplicate detected at commit: invoice with UID '{remarks}' already exists."}

# 		invoice_doc.insert()
# 		invoice_doc.submit()
# 		frappe.db.commit()

# 		return invoice_doc

# 	except Exception as e:
# 		frappe.db.rollback()
# 		frappe.log_error(frappe.get_traceback(), "Invoice Submit Error")
# 		return {
# 			"error": f"Invoice creation halted: {str(e)}",
# 			"status": "not_posted"
# 		}

@frappe.whitelist()
def get_sales_payment_summary(start_date, end_date):
	try:
		# Get the logged-in user's full name
		user_doc = frappe.get_doc("User", frappe.session.user)
		user_full_name = user_doc.full_name

		# Fetch Sales Invoice total for the specified date range and creator, excluding cancelled records
		invoice_total = frappe.db.sql("""
			SELECT SUM(`tabSales Invoice`.grand_total) as total_amount
			FROM `tabSales Invoice`
			WHERE posting_date BETWEEN %s AND %s
			AND docstatus = 1  # Exclude cancelled records (docstatus = 2)
			AND owner = %s
		""", (start_date, end_date, frappe.session.user))[0][0]

		# Fetch Payment Entry total for the specified date range linked to Sales Invoice and creator
		payment_total = frappe.db.sql("""
			SELECT SUM(`tabPayment Entry`.paid_amount) as total_paid_amount
			FROM `tabPayment Entry Reference`
			INNER JOIN `tabPayment Entry` ON `tabPayment Entry Reference`.parent = `tabPayment Entry`.name
			INNER JOIN `tabSales Invoice` ON `tabPayment Entry Reference`.reference_name = `tabSales Invoice`.name
			WHERE `tabPayment Entry`.posting_date BETWEEN %s AND %s
			AND `tabPayment Entry`.docstatus = 1  # Exclude cancelled records (docstatus = 2)
			AND `tabSales Invoice`.owner = %s
		""", (start_date, end_date, frappe.session.user))[0][0]

		data = {
			"user": user_full_name,
			"start_date": start_date,
			"end_date": end_date,
			"total_invoices": invoice_total,
			"total_payments": payment_total,
		}
		return data
	except Exception as e:
		return {"error": str(e)}

@frappe.whitelist()
def cancel_invoice(name=None):
	try:
		# Get the Sales Invoice document
		invoice_doc = frappe.get_doc("Sales Invoice", name)

		# Check if the invoice is already canceled
		if invoice_doc.docstatus == 2:  # 2 represents 'Cancelled'
			return {
				"message": "Invoice is already canceled",
				"status": "error"
			}

		# Cancel the invoice
		invoice_doc.cancel()

		return {
			"message": f"Invoice {name} has been canceled",
			"status": "successfully posted"
		}
	except Exception as e:
		return {
			"message": str(e),
			"status": "error"
		}

@frappe.whitelist(allow_guest=True)
def get_sales_invoice(docname):
	invoice_doc = frappe.get_doc("Sales Invoice",docname)
	return invoice_doc

@frappe.whitelist(allow_guest=True)
def update_invoice(docname,items):
	invoice_doc = frappe.get_doc("Sales Invoice",docname)
	items = json.loads(items)
	for item in invoice_doc.items:
		for i in items:
			if item.item_code == i['item_code']:
				item.qty = i['qty']
	
		
	return invoice_doc.save(ignore_permissions=True)

@frappe.whitelist()
def get_sales_payment_summary(start_date, end_date):
	try:
		# Get the logged-in user's full name
		user_doc = frappe.get_doc("User", frappe.session.user)
		user_full_name = user_doc.full_name

		# Fetch Sales Invoice total for the specified date range and creator, excluding cancelled records
		invoice_total = frappe.db.sql("""
			SELECT SUM(`tabSales Invoice`.grand_total) as total_amount
			FROM `tabSales Invoice`
			WHERE posting_date BETWEEN %s AND %s
			AND docstatus = 1  # Exclude cancelled records (docstatus = 2)
			AND owner = %s
		""", (start_date, end_date, frappe.session.user))[0][0]

		# Fetch Payment Entry total for the specified date range linked to Sales Invoice and creator
		payment_total = frappe.db.sql("""
			SELECT SUM(`tabPayment Entry`.paid_amount) as total_paid_amount
			FROM `tabPayment Entry Reference`
			INNER JOIN `tabPayment Entry` ON `tabPayment Entry Reference`.parent = `tabPayment Entry`.name
			INNER JOIN `tabSales Invoice` ON `tabPayment Entry Reference`.reference_name = `tabSales Invoice`.name
			WHERE `tabPayment Entry`.posting_date BETWEEN %s AND %s
			AND `tabPayment Entry`.docstatus = 1  # Exclude cancelled records (docstatus = 2)
			AND `tabSales Invoice`.owner = %s
		""", (start_date, end_date, frappe.session.user))[0][0]

		data = {
			"user": user_full_name,
			"start_date": start_date,
			"end_date": end_date,
			"total_invoices": invoice_total,
			"total_payments": payment_total,
		}
		return data
	except Exception as e:
		return {"error": str(e)}

# @frappe.whitelist()
# def create_invoice_coupon(
#     customer_name,
#     paid_amount=None,
#     items=None,
#     remarks=None,
#     payments=None,
#     coupon_code=None,
#     mode_of_payment=None,
#     reference_no=None,
#     user=None,
#     is_pos=None,
#     update_stock=None,
#     discount_amount=0,
#     discount_percentage=0,
#     loyalty_points=None,
#     redeem_loyalty_points=None,
#     posting_date=None  # <-- new optional parameter
# ):
#     import time
#     from frappe.utils import flt, getdate, nowdate
#     import json

#     current_user = user or frappe.session.user

#     # ----------------------------------------------------------
#     # DUPLICATE PREVENTION (AT THE VERY TOP)
#     # ----------------------------------------------------------
#     if remarks:
#         exists = frappe.db.exists("Sales Invoice", {"remarks": remarks})
#         if exists:
#             return {
#                 "error": f"Duplicate prevented: Invoice with UID '{remarks}' already exists ({exists}).",
#                 "status": "not_posted"
#             }

#     if reference_no:
#         ref_exists = frappe.db.exists("Sales Invoice Payment", {"reference_no": reference_no})
#         if ref_exists:
#             return {
#                 "error": f"Duplicate payment reference: {reference_no} already used ({ref_exists}).",
#                 "status": "not_posted"
#             }

#     # ----------------------------------------------------------

#     # --- Validation: Customer must be selected ---
#     if not customer_name:
#         return {
#             "error": "Cannot create invoice: Customer not selected.",
#             "status": "not_posted"
#         }

#     # --- Parse Inputs ---
#     if isinstance(items, str):
#         items = json.loads(items)
#     if isinstance(payments, str):
#         payments = json.loads(payments)

#     # --- Get Warehouse ---
#     fallback_warehouse = frappe.get_all(
#         "User Permission",
#         filters={"user": current_user, "allow": "Warehouse", "is_default": 0},
#         fields=["for_value"]
#     )

#     fallback_warehouse = (
#         fallback_warehouse[0]["for_value"]
#         if fallback_warehouse else frappe.db.get_single_value("Stock Settings", "default_warehouse")
#     )

#     if not fallback_warehouse:
#         return {
#             "error": "No warehouse assigned to user and no default warehouse in Stock Settings."
#         }

#     # --- Get POS Profile if applicable ---
#     pos_profile = pos_warehouse = fulfillment_branch = company = cost_center = None

#     if is_pos:
#         result = frappe.db.sql("""
#             SELECT ppu.parent
#             FROM `tabPOS Profile User` ppu
#             JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
#             WHERE ppu.user = %s AND ppu.default = 1 AND pp.disabled = 0
#             LIMIT 1
#         """, (current_user,), as_dict=0)

#         if result:
#             pos_profile = result[0][0]
#             pos_warehouse = frappe.db.get_value("POS Profile", pos_profile, "warehouse")
#             fulfillment_branch = frappe.db.get_value("POS Profile", pos_profile, "fulfillment_branch_")
#             cost_center = frappe.db.get_value("POS Profile", pos_profile, "cost_center")
#             company = frappe.db.get_value("POS Profile", pos_profile, "company")
#         else:
#             return {"error": f"No enabled default POS Profile found for user '{current_user}'."}

#     # --- Assign Warehouse and Cost Center to Items ---
#     if is_pos or update_stock:
#         for item in items or []:
#             item["warehouse"] = pos_warehouse or fallback_warehouse
#             item["cost_center"] = cost_center
#         update_stock = 1

#     # --- Payment Entries ---
#     payment_entries = []

#     if payments:
#         for p in payments:
#             mode = p.get("mode_of_payment")
#             amount = flt(p.get("amount") or 0)
#             reference = p.get("reference_no")

#             if amount > 0:
#                 payment_entries.append({
#                     "mode_of_payment": mode,
#                     "amount": amount,
#                     "reference_no": reference
#                 })

#     elif mode_of_payment and paid_amount:
#         payment_entries.append({
#             "mode_of_payment": mode_of_payment,
#             "amount": flt(paid_amount),
#             "reference_no": reference_no
#         })

#     # --- Prepare Invoice Data --- 
#     invoice_doc_data = {
#         "doctype": "Sales Invoice",
#         "customer": customer_name,
#         "company": company,
#         "remarks": remarks,
#         "custom_from": "GormPos",
#         "fulfillment_branch_": fulfillment_branch,
#         "cost_center": cost_center,
#         "update_stock": update_stock,
#         "confirm_branch": 1,
#         "is_pos": is_pos,
#         "items": items or [],
#         "discount_amount": discount_amount,
#         "additional_discount_percentage": discount_percentage,
#         "apply_discount_on": "Grand Total",
#         "is_cash_or_non_trade_discount": 1,
#         "payments": payment_entries,
#         "redeem_loyalty_points": redeem_loyalty_points,
#         "loyalty_points": flt(loyalty_points),
#     }

#     # --- Set posting date ---
#     if posting_date:
#         try:
#             invoice_doc_data["posting_date"] = getdate(posting_date)
#             invoice_doc_data["set_posting_time"] = 1
#         except Exception as e:
#             return {"error": f"Invalid posting date: {posting_date}. Error: {str(e)}"}
#     else:
#         invoice_doc_data["posting_date"] = nowdate()

#     if is_pos:
#         invoice_doc_data["pos_profile"] = pos_profile

#     # --- Coupon discount ---
#     discount_account = None
#     discount_amount = 0.0
#     discount_percent = 0.0

#     if coupon_code:
#         discount_doc = frappe.get_all(
#             "Coupon Code",
#             filters={"custom_company": company, "name": coupon_code},
#             fields=["custom_discount_account", "custom_discount_amount", "custom_discount_percent"]
#         )

#         if discount_doc:
#             discount_account = discount_doc[0].get("custom_discount_account")
#             discount_amount = flt(discount_doc[0].get("custom_discount_amount") or 0)
#             discount_percent = flt(discount_doc[0].get("custom_discount_percent") or 0)

#             if discount_account:
#                 invoice_doc_data["additional_discount_account"] = discount_account
#             if discount_amount > 0:
#                 invoice_doc_data["discount_amount"] = discount_amount
#             elif discount_percent > 0:
#                 invoice_doc_data["additional_discount_percentage"] = discount_percent

#             invoice_doc_data["custom_coupon_code"] = str(coupon_code)

#     # --- Insert and Submit with Retry ---
#     MAX_RETRIES = 3

#     for attempt in range(MAX_RETRIES):
#         try:
#             invoice_doc = frappe.get_doc(invoice_doc_data)

#             # SAFETY DUPLICATE CHECK BEFORE COMMIT
#             if remarks and frappe.db.exists("Sales Invoice", {"remarks": remarks}):
#                 return {
#                     "error": f"Duplicate detected at commit: invoice with UID '{remarks}' already exists."
#                 }

#             invoice_doc.insert()
#             invoice_doc.submit()
#             frappe.db.commit()

#             return invoice_doc

#         except Exception as e:
#             frappe.db.rollback()

#             msg = str(e)

#             if ("Lock wait timeout" in msg or "deadlock" in msg.lower()) and attempt < MAX_RETRIES - 1:
#                 time.sleep(0.4)
#                 continue

#             frappe.log_error(frappe.get_traceback(), "Invoice Submit Error")

#             return {
#                 "error": f"Invoice creation halted: {str(e)}",
#                 "status": "not_posted"
#             }


# import frappe
# import time
# from frappe.utils import flt, getdate, nowdate
# import json

# @frappe.whitelist()
# def create_invoice_coupon(
#     customer_name,
#     paid_amount=None,
#     items=None,
#     remarks=None,
#     payments=None,
#     coupon_code=None,
#     mode_of_payment=None,
#     reference_no=None,
#     user=None,
#     is_pos=None,
#     update_stock=None,
#     discount_amount=0,
#     discount_percentage=0,
#     loyalty_points=None,
#     redeem_loyalty_points=None,
#     posting_date=None
# ):
#     current_user = user or frappe.session.user

#     # ----------------------------------------------------------
#     # USE USER PROVIDED REMARKS AND SAVE TO UID TRACKER
#     # ----------------------------------------------------------
#     if not remarks:
#         return {"error": "Cannot create invoice: 'remarks' must be provided.", "status": "not_posted"}

#     try:
#         # Save in Invoice UID Tracker
#         tracker_doc = frappe.get_doc({"doctype": "Invoice UID Tracker", "uid": remarks})
#         tracker_doc.insert(ignore_permissions=True)
#         frappe.db.commit()
#     except frappe.DuplicateEntryError:
#         frappe.db.rollback()
#         return {"error": f"Duplicate UID: '{remarks}' already exists in Invoice UID Tracker.", "status": "not_posted"}
#     except Exception as e:
#         frappe.db.rollback()
#         return {"error": f"Failed to create UID Tracker entry: {str(e)}", "status": "not_posted"}

#     # --- Validation: Customer must be selected ---
#     if not customer_name:
#         return {"error": "Cannot create invoice: Customer not selected.", "status": "not_posted"}

#     # --- Parse Inputs ---
#     if isinstance(items, str):
#         items = json.loads(items)
#     if isinstance(payments, str):
#         payments = json.loads(payments)

#     # --- Get Warehouse ---
#     fallback_warehouse = frappe.get_all(
#         "User Permission",
#         filters={"user": current_user, "allow": "Warehouse", "is_default": 0},
#         fields=["for_value"]
#     )
#     fallback_warehouse = (
#         fallback_warehouse[0]["for_value"]
#         if fallback_warehouse else frappe.db.get_single_value("Stock Settings", "default_warehouse")
#     )
#     if not fallback_warehouse:
#         return {"error": "No warehouse assigned to user and no default warehouse in Stock Settings."}

#     # --- Get POS Profile if applicable ---
#     pos_profile = pos_warehouse = fulfillment_branch = company = cost_center = None
#     if is_pos:
#         result = frappe.db.sql("""
#             SELECT ppu.parent
#             FROM `tabPOS Profile User` ppu
#             JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
#             WHERE ppu.user = %s AND ppu.default = 1 AND pp.disabled = 0
#             LIMIT 1
#         """, (current_user,), as_dict=0)

#         if result:
#             pos_profile = result[0][0]
#             pos_warehouse = frappe.db.get_value("POS Profile", pos_profile, "warehouse")
#             fulfillment_branch = frappe.db.get_value("POS Profile", pos_profile, "fulfillment_branch_")
#             cost_center = frappe.db.get_value("POS Profile", pos_profile, "cost_center")
#             company = frappe.db.get_value("POS Profile", pos_profile, "company")
#         else:
#             return {"error": f"No enabled default POS Profile found for user '{current_user}'."}

#     # --- Assign Warehouse and Cost Center to Items ---
#     if is_pos or update_stock:
#         for item in items or []:
#             item["warehouse"] = pos_warehouse or fallback_warehouse
#             item["cost_center"] = cost_center
#         update_stock = 1

#     # --- Payment Entries ---
#     payment_entries = []
#     if payments:
#         for p in payments:
#             amount = flt(p.get("amount") or 0)
#             if amount > 0:
#                 payment_entries.append({
#                     "mode_of_payment": p.get("mode_of_payment"),
#                     "amount": amount,
#                     "reference_no": p.get("reference_no")
#                 })
#     elif mode_of_payment and paid_amount:
#         payment_entries.append({
#             "mode_of_payment": mode_of_payment,
#             "amount": flt(paid_amount),
#             "reference_no": reference_no
#         })

#     # --- Prepare Invoice Data ---
#     invoice_doc_data = {
#         "doctype": "Sales Invoice",
#         "customer": customer_name,
#         "company": company,
#         "remarks": remarks,  # Use the UID from tracker
#         "custom_from": "GormPos",
#         "fulfillment_branch_": fulfillment_branch,
#         "cost_center": cost_center,
#         "update_stock": update_stock,
#         "confirm_branch": 1,
#         "is_pos": is_pos,
#         "items": items or [],
#         "discount_amount": discount_amount,
#         "additional_discount_percentage": discount_percentage,
#         "apply_discount_on": "Grand Total",
#         "is_cash_or_non_trade_discount": 1,
#         "payments": payment_entries,
#         "redeem_loyalty_points": redeem_loyalty_points,
#         "loyalty_points": flt(loyalty_points),
#         "posting_date": nowdate(),
#     }

#     # --- Set posting date if provided ---
#     if posting_date:
#         try:
#             invoice_doc_data["posting_date"] = getdate(posting_date)
#             invoice_doc_data["set_posting_time"] = 1
#         except Exception as e:
#             return {"error": f"Invalid posting date: {posting_date}. Error: {str(e)}"}

#     if is_pos:
#         invoice_doc_data["pos_profile"] = pos_profile

#     # --- Coupon discount ---
#     if coupon_code:
#         discount_doc = frappe.get_all(
#             "Coupon Code",
#             filters={"custom_company": company, "name": coupon_code},
#             fields=["custom_discount_account", "custom_discount_amount", "custom_discount_percent"]
#         )
#         if discount_doc:
#             disc = discount_doc[0]
#             if disc.get("custom_discount_account"):
#                 invoice_doc_data["additional_discount_account"] = disc["custom_discount_account"]
#             if flt(disc.get("custom_discount_amount") or 0) > 0:
#                 invoice_doc_data["discount_amount"] = flt(disc["custom_discount_amount"])
#             elif flt(disc.get("custom_discount_percent") or 0) > 0:
#                 invoice_doc_data["additional_discount_percentage"] = flt(disc["custom_discount_percent"])
#             invoice_doc_data["custom_coupon_code"] = str(coupon_code)

#     # --- Insert and Submit with Retry ---
#     MAX_RETRIES = 3
#     for attempt in range(MAX_RETRIES):
#         try:
#             invoice_doc = frappe.get_doc(invoice_doc_data)
#             invoice_doc.insert()
#             invoice_doc.submit()
#             frappe.db.commit()
#             return invoice_doc
#         except Exception as e:
#             frappe.db.rollback()
#             msg = str(e)
#             if ("Lock wait timeout" in msg or "deadlock" in msg.lower()) and attempt < MAX_RETRIES - 1:
#                 time.sleep(0.4)
#                 continue
#             frappe.log_error(frappe.get_traceback(), "Invoice Submit Error")
#             return {"error": f"Invoice creation halted: {str(e)}", "status": "not_posted"}
