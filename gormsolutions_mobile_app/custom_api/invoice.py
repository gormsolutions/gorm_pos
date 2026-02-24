import frappe
import json

@frappe.whitelist(allow_guest=True)
def get_invoice_details(limit, offset, search=None):
	# Initialize filters with docstatus filter
	filters = [["docstatus", "=", 1]]

	# Add a filter for the logged-in user
	filters.append(["owner", "=", frappe.session.user])

	# If a search term is provided, add a filter for customer_name
	if search:
		filters.append(["customer_name", "like", f"%{search}%"])

	# Fetch filtered Sales Invoice details
	sales_invoice_details = frappe.get_all(
		'Sales Invoice',
		fields=[
			'name', 'grand_total', 'remarks','posting_date','posting_time', 'paid_amount', 'outstanding_amount',
			'owner', 'docstatus', 'status', 'customer', 'customer_name'
		],
		order_by='posting_date desc',
		filters=filters,
		start=offset,
		page_length=limit
	)

	# Fetch and attach items for each invoice
	for invoice in sales_invoice_details:
		invoice["items"] = frappe.get_all(
			"Sales Invoice Item",
			fields=["item_code", "item_name", "qty", "uom","rate", "amount"],
			filters={"parent": invoice["name"]}
		)

	return sales_invoice_details



import frappe
import json

@frappe.whitelist(allow_guest=True)
def get_cancelled_invoice_details(limit, offset, search=None):
	# Initialize filters with docstatus filter
	filters = [["docstatus", "=", 2]]

	# Add a filter for the logged-in user
   
	# If a search term is provided, add a filter for customer_name
	if search:
		filters.append(["customer_name", "like", f"%{search}%"])

	# Fetch filtered Sales Invoice details
	sales_invoice_details = frappe.get_all(
		'Sales Invoice',
		fields=[
			'name', 'grand_total', 'remarks','posting_date','posting_time', 'paid_amount', 'outstanding_amount',
			'owner', 'docstatus', 'status', 'customer', 'customer_name'
		],
		order_by='posting_date desc',
		filters=filters,
		start=offset,
		page_length=limit
	)

	# Fetch and attach items for each invoice
	for invoice in sales_invoice_details:
		invoice["items"] = frappe.get_all(
			"Sales Invoice Item",
			fields=["item_code", "item_name", "qty", "uom","rate", "amount"],
			filters={"parent": invoice["name"]}
		)

	return sales_invoice_details

@frappe.whitelist()
def create_invoice(customer_name, paid_amount, items,remarks=None, mode_of_payment=None,reference_no=None,user=None, is_pos=None, update_stock=None, discount_amount=0, discount_percentage=0):
	import json

	# Parse items if necessary
	if isinstance(items, str):
		items = json.loads(items)

	# Get the current user
	current_user = frappe.session.user

	# Fetch User Permission records for 'Warehouse' allowed for the current user
	fallback_warehouse = frappe.get_all(
		'User Permission',
		filters={
			'user': current_user,
			'allow': 'Warehouse',
			"is_default": 1
		},
		fields=['for_value']
	)

	# Determine the fallback warehouse value
	fallback_warehouse = fallback_warehouse[0]['for_value'] if fallback_warehouse else None

	if not fallback_warehouse:
		# Set a default warehouse if no user permissions are found
		fallback_warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse')
		if not fallback_warehouse:
			return {"error": "No warehouse assigned to user and no default warehouse found in Stock Settings."}

	pos_profile = None
	pos_warehouse = None
	

	# If user is provided and is_pos is enabled, fetch POS profile
	if user and is_pos:
		pos_profile = frappe.db.get_value("POS Profile User", {"default": 1, "user": user}, "parent")
		pos_warehouse = frappe.db.get_value("POS Profile", pos_profile, "warehouse")

	# Set warehouse and enable update_stock if is_pos or update_stock is enabled
	if is_pos or update_stock:
		for item in items:
			# Use POS warehouse if available, else fallback to user-defined or default warehouse
			item['warehouse'] = pos_warehouse or fallback_warehouse
		update_stock = 1  # Explicitly enable update_stock

	try:
		# Construct the Sales Invoice document
		invoice_doc_data = {
			"doctype": "Sales Invoice",
			"customer": customer_name,
			"remarks":remarks,
			"update_stock": update_stock,  # Ensure update_stock is enabled
			"is_pos": is_pos,  # Use the value passed by the user
			"items": items,
			"discount_amount": discount_amount,  # Apply discount amount
			"additional_discount_percentage": discount_percentage,  # Apply discount percentage
			"apply_discount_on": "Grand Total",  # Choose to apply discount on Grand Total
			"payments": [{
				"mode_of_payment": mode_of_payment,  # Using the first permitted mode of payment
				"amount": paid_amount,
				"reference_no":reference_no
			}]
		}

		# Include POS profile only if is_pos is enabled
		if is_pos:
			invoice_doc_data["pos_profile"] = pos_profile

		# Create and submit the invoice
		invoice_doc = frappe.get_doc(invoice_doc_data)
		res_doc = invoice_doc.insert(ignore_permissions=True)
		res_doc.submit()
		return res_doc

	except Exception as e:
		return {"error": str(e)}

@frappe.whitelist()
def create_invoices(customer_name, paid_amount, items, remarks=None, 
					mode_of_payment=None, reference_no=None, user=None, 
					is_pos=None, update_stock=None, discount_amount=0, 
					discount_percentage=0, payments=None):

	import json
	import frappe

	try:
		# -----------------------
		# Parse JSON inputs
		# -----------------------
		if isinstance(items, str):
			items = json.loads(items)

		if payments and isinstance(payments, str):
			payments = json.loads(payments)

		current_user = frappe.session.user

		# -----------------------
		# Get fallback warehouse
		# -----------------------
		fallback_warehouse = frappe.get_all(
			'User Permission',
			filters={
				'user': current_user,
				'allow': 'Warehouse',
				"is_default": 1
			},
			fields=['for_value']
		)

		fallback_warehouse = fallback_warehouse[0]['for_value'] if fallback_warehouse else None

		if not fallback_warehouse:
			fallback_warehouse = frappe.db.get_single_value(
				'Stock Settings', 
				'default_warehouse'
			)

		if not fallback_warehouse:
			return {
				"error": "No warehouse assigned to user and no default warehouse found in Stock Settings."
			}

		# -----------------------
		# POS Handling
		# -----------------------
		pos_profile = None
		pos_warehouse = None

		if user and is_pos:
			pos_profile = frappe.db.get_value(
				"POS Profile User",
				{"default": 1, "user": user},
				"parent"
			)

			if pos_profile:
				pos_warehouse = frappe.db.get_value(
					"POS Profile",
					pos_profile,
					"warehouse"
				)

		# -----------------------
		# Assign warehouse & force stock update
		# -----------------------
		if is_pos or update_stock:
			for item in items:
				item['warehouse'] = pos_warehouse or fallback_warehouse
			update_stock = 1

		# -----------------------
		# STOCK VALIDATION
		# -----------------------
		if update_stock:
			for item in items:
				item_code = item.get("item_code")
				warehouse = item.get("warehouse")
				qty = float(item.get("qty", 0))

				if not item_code:
					return {"error": "Item Code is required."}

				actual_qty = frappe.db.get_value(
					"Bin",
					{"item_code": item_code, "warehouse": warehouse},
					"actual_qty"
				) or 0

				if actual_qty < qty:
					return {
						"error": f"Insufficient stock for Item '{item_code}' in Warehouse '{warehouse}'. "
								 f"Available Qty: {actual_qty}, Required Qty: {qty}"
					}

		# -----------------------
		# Create Invoice
		# -----------------------
		invoice_doc_data = {
			"doctype": "Sales Invoice",
			"customer": customer_name,
			"remarks": remarks,
			"update_stock": update_stock,
			"is_pos": is_pos,
			"items": items,
			"discount_amount": discount_amount,
			"additional_discount_percentage": discount_percentage,
			"apply_discount_on": "Grand Total"
		}

		# -----------------------
		# POS Payments
		# -----------------------
		if is_pos:
			invoice_doc_data["pos_profile"] = pos_profile
			invoice_doc_data["paid_amount"] = paid_amount
			invoice_doc_data["payments"] = []

			if payments:
				for payment in payments:
					mop = payment.get("mode_of_payment")

					if not frappe.db.exists("Mode of Payment", mop):
						frappe.throw(f"Mode of Payment '{mop}' does not exist.")

					invoice_doc_data["payments"].append({
						"mode_of_payment": mop,
						"amount": payment.get("amount", 0),
						"reference_no": payment.get("reference_no")
					})

		# -----------------------
		# Insert & Submit
		# -----------------------
		invoice_doc = frappe.get_doc(invoice_doc_data)
		invoice_doc.flags.ignore_permissions = True
		invoice_doc.insert()
		invoice_doc.submit()

		return invoice_doc

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Create Invoice Error")
		return {"error": str(e)}



@frappe.whitelist()
def create_invoices_mj(customer_name, paid_amount, items, remarks=None, 
					mode_of_payment=None, reference_no=None, user=None, 
					is_pos=None, update_stock=None, discount_amount=0, 
					discount_percentage=0, payments=None):
	
	import json

	if isinstance(items, str):
		items = json.loads(items)

	if payments and isinstance(payments, str):
		payments = json.loads(payments)

	current_user = frappe.session.user

	fallback_warehouse = frappe.get_all(
		'User Permission',
		filters={
			'user': current_user,
			'allow': 'Warehouse',
			"is_default": 0
		},
		fields=['for_value']
	)

	fallback_warehouse = fallback_warehouse[0]['for_value'] if fallback_warehouse else None

	if not fallback_warehouse:
		fallback_warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse')
		if not fallback_warehouse:
			return {"error": "No warehouse assigned to user and no default warehouse found in Stock Settings."}

	pos_profile = None
	pos_warehouse = None
	cost_center = None  # ✅ initialize

	if user and is_pos:
		pos_profile = frappe.db.get_value("POS Profile User", {"default": 1, "user": user}, "parent")
		pos_warehouse = frappe.db.get_value("POS Profile", pos_profile, "warehouse")
		cost_center = frappe.db.get_value("POS Profile", pos_profile, "cost_center")

	if is_pos or update_stock:
		for item in items:
			item['warehouse'] = pos_warehouse or fallback_warehouse
			item['cost_center'] = cost_center  # Set cost center for each item
		update_stock = 1

	# STOCK VALIDATION
	# -----------------------
	if update_stock:
		for item in items:
			item_code = item.get("item_code")
			warehouse = item.get("warehouse")
			qty = float(item.get("qty", 0))

			if not item_code:
				return {"error": "Item Code is required."}

			actual_qty = frappe.db.get_value(
				"Bin",
				{"item_code": item_code, "warehouse": warehouse},
				"actual_qty"
			) or 0

			if actual_qty < qty:
				return {
					"error": f"Insufficient stock for Item '{item_code}' in Warehouse '{warehouse}'. "
								f"Available Qty: {actual_qty}, Required Qty: {qty}"
				}


	try:
		invoice_doc_data = {
			"doctype": "Sales Invoice",
			"customer": customer_name,
			"cost_center": cost_center,
			"remarks": remarks,
			"update_stock": update_stock,
			"is_pos": is_pos,
			"items": items,
			"discount_amount": discount_amount,
			"additional_discount_percentage": discount_percentage,
			"apply_discount_on": "Grand Total"
		}

		if is_pos:
			invoice_doc_data["pos_profile"] = pos_profile
			invoice_doc_data["paid_amount"] = paid_amount
			invoice_doc_data["payments"] = []

			if payments:
				for payment in payments:
					if not frappe.db.exists("Mode of Payment", payment.get("mode_of_payment")):
						frappe.throw(f"Mode of Payment '{payment.get('mode_of_payment')}' does not exist.")
					
					invoice_doc_data["payments"].append({
						"mode_of_payment": payment.get("mode_of_payment"),
						"amount": payment.get("amount", 0),
						"reference_no": payment.get("reference_no")
					})

		invoice_doc = frappe.get_doc(invoice_doc_data)
		res_doc = invoice_doc.insert(ignore_permissions=True)
		res_doc.submit()
		return res_doc

	except Exception as e:
		return {"error": str(e)}


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

import frappe
from frappe.utils import now

@frappe.whitelist(allow_guest=False)
def cancel_invoice(name=None):
	"""
	Cancels a submitted Sales Invoice (docstatus=1) safely.
	Includes permission checks, rollback on error, and activity logging.
	"""
	if not name:
		return {
			"status": "error",
			"message": "Invoice name is required."
		}

	try:
		# Fetch the invoice document
		invoice_doc = frappe.get_doc("Sales Invoice", name)

		# Permission check — only allow users with cancel rights
		if not frappe.has_permission("Sales Invoice", "cancel", invoice_doc):
			return {
				"status": "error",
				"message": "You do not have permission to cancel this invoice."
			}

		# Check current document status
		if invoice_doc.docstatus == 2:
			return {
				"status": "error",
				"message": f"Invoice {name} is already canceled."
			}

		if invoice_doc.docstatus != 1:
			return {
				"status": "error",
				"message": f"Invoice {name} is not submitted and cannot be canceled."
			}

		# Cancel the invoice
		invoice_doc.cancel()

		# Commit transaction
		frappe.db.commit()

		# Log cancellation in system log
		frappe.logger("sales_invoice").info({
			"action": "cancel_invoice",
			"invoice": name,
			"user": frappe.session.user,
			"timestamp": now()
		})

		return {
			"status": "success",
			"message": f"Invoice {name} has been successfully canceled."
		}

	except frappe.DoesNotExistError:
		frappe.db.rollback()
		return {
			"status": "error",
			"message": f"Invoice {name} does not exist."
		}

	except frappe.ValidationError as ve:
		frappe.db.rollback()
		return {
			"status": "error",
			"message": f"Validation Error: {str(ve)}"
		}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=str(e), title="Cancel Invoice Error")
		return {
			"status": "error",
			"message": f"Failed to cancel invoice {name}: {str(e)}"
		}


@frappe.whitelist(allow_guest=True)
def get_sales_invoice(docname):
	invoice_doc = frappe.get_doc("Sales Invoice",docname)
	return invoice_doc

@frappe.whitelist()
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