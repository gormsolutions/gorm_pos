import frappe
from frappe import _

@frappe.whitelist()  # Allow guest access if required
def create_material_request():
	try:
		# Get request data from Flutter app
		data = frappe.local.form_dict  # Get raw form data
		doc = frappe.parse_json(data)  # Convert to JSON object

		# Create a Material Request
		material_request = frappe.new_doc("Material Request")
		material_request.material_request_type = "Material Transfer"
		material_request.transaction_date = frappe.utils.today()
		material_request.schedule_date = frappe.utils.today()

		current_user = frappe.session.user

		# Fetch default warehouse from User Permissions
		user_permissions = frappe.get_all(
			"User Permission",
			filters={"user": current_user, "allow": "Warehouse","is_default": 0},
			fields=["for_value"]
		)
		default_warehouses = [perm["for_value"] for perm in user_permissions]

		# Use the first warehouse if multiple exist
		source_warehouse = default_warehouses[0] if default_warehouses else None

		if not source_warehouse:
			frappe.throw("Source warehouse not found. Please set it in User Permissions.")

	  
		for item in doc.get("items", []):
			material_request.append("items", {
				"item_code": item.get("item_code"),
				"schedule_date": frappe.utils.today(),  # Required field
				"qty": item.get("qty"),
				"uom": item.get("uom"),
				"warehouse": source_warehouse  # Set as required warehouse
			})

		material_request.insert()
		material_request.submit()

		return {"status": "success", "message": "Material Request successfully created.", "material_request": material_request.name}
	except Exception as e:
		frappe.log_error(_("Error creating Material Request: {0}").format(str(e)))
		return {"status": "error", "message": _("Error creating Material Request. Please try again.")}

@frappe.whitelist()
def get_material_requests():
	try:
		current_user = frappe.session.user
		# Fetch all Material Requests for Material Transfer
		
		material_requests = frappe.get_all(
			"Material Request",
			filters={
				"material_request_type": "Material Transfer",
				"owner": ["!=", current_user]  # Exclude requests created by the current user
				},
			fields=["name", "material_request_type", "transaction_date", "schedule_date","status","per_ordered","owner"]
		)
		
		material_requests_ower = frappe.get_all(
			"Material Request",
			filters={
				"material_request_type": "Material Transfer",
				"owner": ["=", current_user]  # Exclude requests created by the current user
				},
			fields=["name", "material_request_type", "transaction_date", "schedule_date","status","per_ordered","owner"]
		)
		owner_result = []

		results = []
		for req in material_requests:
			# Fetch items for each Material Request
			items = frappe.get_all(
				"Material Request Item",
				filters={"parent": req["name"]},
				fields=["item_code", "schedule_date as required_by", "qty", "warehouse as target_warehouse", "uom"]
			)

			# Add request details and items
			results.append({
				"material_request": req["name"],
				"material_status": req["status"],
				"owner": req["owner"],
				"percentaged_ordered": req["per_ordered"],
				"material_request_type": req["material_request_type"],
				"transaction_date": req["transaction_date"],
				"schedule_date": req["schedule_date"],
				"items": items
			})
		for req_owner in material_requests_ower:
			# Fetch items for each Material Request
			items = frappe.get_all(
				"Material Request Item",
				filters={"parent": req_owner["name"]},
				fields=["item_code", "schedule_date as required_by", "qty", "warehouse as target_warehouse", "uom"]
			)

			# Add request details and items
			owner_result.append({
				"material_request": req_owner["name"],
				"material_status": req_owner["status"],
				"owner": req_owner["owner"],
				"percentaged_ordered": req_owner["per_ordered"],
				"material_request_type": req_owner["material_request_type"],
				"transaction_date": req_owner["transaction_date"],
				"schedule_date": req_owner["schedule_date"],
				"items": items
			})

		return {
			"data": results,
			"data_owner": owner_result
		}

	except Exception as e:
		frappe.log_error(_("Error fetching Material Requests: {0}").format(str(e)))
		return {
			"status": "error",
			"message": _("Error fetching Material Requests."),
			"error_detail": str(e)
		}

@frappe.whitelist()
def create_material_transfer(material_request_name, item_quantities=None):
	try:
		# Fetch the Material Request
		material_request = frappe.get_doc("Material Request", material_request_name)

		if not material_request or material_request.docstatus != 1:
			frappe.throw(_("Invalid Material Request or not submitted."))

		current_user = frappe.session.user

		# Fetch default warehouse from User Permissions (Source Warehouse)
		user_permissions = frappe.get_all(
			"User Permission",
			filters={"user": current_user, "allow": "Warehouse", "is_default": 0},
			fields=["for_value"]
		)
		default_warehouses = [perm["for_value"] for perm in user_permissions]
		source_warehouse = default_warehouses[0] if default_warehouses else None

		if not source_warehouse:
			frappe.throw(_("Source warehouse not found. Please set it in User Permissions."))

		# Parse item quantities from JSON string to Python dictionary
		if isinstance(item_quantities, str):
			import json
			item_quantities = json.loads(item_quantities)

		# Create a Stock Entry (Material Transfer)
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.posting_date = frappe.utils.today()

		total_percentage = 0  # To calculate the average `per_ordered`
		item_count = 0  # Count valid transfer items
		all_fully_transferred = True  # Flag to check if all items are fully transferred

		# Transfer each item
		for item in material_request.items:
			if not item.warehouse:
				frappe.throw(_("Target warehouse is missing for item {0}. Please check Material Request.").format(item.item_code))

			# Skip transfer if source and target warehouses are the same
			if source_warehouse == item.warehouse:
				frappe.msgprint(_("Skipping item {0} as source and target warehouses are the same.").format(item.item_code))
				continue

			# Get the transfer quantity from input, default to full quantity if not specified
			transferred_qty = item_quantities.get(item.item_code, item.qty)

			# Ensure transferred quantity does not exceed requested quantity
			if transferred_qty > item.qty:
				frappe.throw(_("Transfer quantity cannot exceed requested quantity for item {0}.").format(item.item_code))

			per_ordered = (transferred_qty / item.qty) * 100  # Calculate transfer percentage

			# Append item to Stock Entry
			stock_entry.append("items", {
				"item_code": item.item_code,
				"qty": transferred_qty,
				"uom": item.uom,
				"s_warehouse": source_warehouse,  # Source warehouse from user permissions
				"t_warehouse": item.warehouse  # Target warehouse from Material Request child table
			})

			# Accumulate percentages for overall per_ordered calculation
			total_percentage += per_ordered
			item_count += 1

			# If any item is not fully transferred, update flag
			if per_ordered < 100:
				all_fully_transferred = False

		# Ensure there are valid items before inserting
		if item_count == 0:
			frappe.throw(_("No valid items to transfer. All had the same source and target warehouse."))

		# Insert & submit Stock Entry
		stock_entry.insert()
		stock_entry.submit()

		# Calculate average per_ordered for Material Request
		overall_per_ordered = total_percentage / item_count if item_count else 0

		# Update Material Request
		material_request.db_set({
			"per_ordered": overall_per_ordered,
			"status": "Transferred" if all_fully_transferred else "Partially Transferred"
		})

		return {
			"status": "success",
			"message": "Material Transfer created successfully.",
			"stock_entry": stock_entry.name,
			"material_request": material_request.name,
			"per_ordered": overall_per_ordered
		}

	except Exception as e:
		frappe.log_error(_("Error creating Material Transfer: {0}").format(str(e)))
		return {
			"status": "error",
			"message": _("Error creating Material Transfer. Please try again."),
			"error_detail": str(e)
		}

@frappe.whitelist()
def stop_material_request(material_request_name):
	"""Stops a Material Request by setting its status to 'Stopped'."""
	try:
		# Fetch the Material Request document
		material_request = frappe.get_doc("Material Request", material_request_name)

		# Ensure the document exists and is submitted
		if not material_request or material_request.docstatus != 1:
			frappe.throw(_("Only submitted Material Requests can be stopped."))

		# Set status to "Stopped"
		material_request.db_set("status", "Stopped")

		return {
			"status": "success",
			"message": f"Material Request {material_request_name} has been stopped."
		}

	except Exception as e:
		frappe.log_error(_("Error stopping Material Request: {0}").format(str(e)))
		return {
			"status": "error",
			"message": _("Error stopping Material Request. Please try again."),
			"error_detail": str(e)
		}

import frappe
@frappe.whitelist()
def create_item_prices_for_all_items():
	# Fetch all items
	items = frappe.get_all("Item", fields=["item_code"])

	for item in items:
		item_code = item["item_code"]
		
		# Fetch UOM Conversion Details for the current item
		conversion_details = frappe.get_all(
			"UOM Conversion Detail",
			filters={"parent": item_code},
			fields=["uom"]
		)

		for conversion in conversion_details:
			uom = conversion["uom"]
			
			# Check if the price already exists in the Item Price list for this item and UOM
			existing_price = frappe.get_all(
				"Item Price", 
				filters={"item_code": item_code, "uom": uom}, 
				fields=["name"]
			)

			if not existing_price:
				# If no price exists, fetch the price from the Sales Invoice Item
				sales_invoice_item = frappe.get_all(
					"Sales Invoice Item", 
					filters={"item_code": item_code, "uom": uom}, 
					fields=["rate"],
					limit=1  # Fetch only one price
				)

				if sales_invoice_item:
					rate = sales_invoice_item[0]["rate"]
					price_list = "Standard Selling"  # Replace with the correct Price List if needed
					create_price_entry(item_code, uom, rate, price_list)
				else:
					frappe.msgprint(f"No sales invoice price found for {item_code} with UOM {uom}. Skipping creation.")
			else:
				# Skip if price already exists
				frappe.msgprint(f"Price already exists for {item_code} with UOM {uom}. Skipping creation.")

def create_price_entry(item_code, uom, rate, price_list):
	# Create a new price entry for the item in the price list
	new_price = frappe.get_doc({
		"doctype": "Item Price",
		"item_code": item_code,
		"price_list": price_list,
		"uom": uom,
		"price_list_rate": rate,
		"selling": 1  # Set to 1 for selling price
	})
	new_price.insert()
	frappe.db.commit()  # Commit the changes to the database
	frappe.msgprint(f"Price created for {item_code} with UOM {uom} and rate {rate}.")

# Call the function to create item prices for all items
create_item_prices_for_all_items()

@frappe.whitelist()
def fetch_items_without_prices():
	# Fetch items that are not disabled
	items_without_prices = frappe.get_all(
		"Item",
		fields=["item_code", "item_name"],
		filters={"disabled": 0},  # Optional: Exclude disabled items
	)

	# List to store the results
	results = []

	# Loop through each item
	for item in items_without_prices:
		item_code = item["item_code"]

		# Fetch UOM Conversion Details for the item
		conversion_details = frappe.get_all(
			"UOM Conversion Detail", 
			filters={"parent": item_code},
			fields=["uom"]
		)

		# Loop through each UOM conversion for the item
		for conversion in conversion_details:
			uom = conversion["uom"]

			# Check if the item has any price in the Item Price list for the specific UOM
			existing_price = frappe.get_all(
				"Item Price", 
				filters={"item_code": item_code, "uom": uom},
				fields=["item_code"]
			)

			# If no price exists for this item and UOM, add it to the result
			if not existing_price:
				results.append({"item_code": item_code, "item_name": item["item_name"], "uom": uom})

	if results:
		return results  # Return the data as a list of dictionaries
	else:
		return "No items without prices found."

@frappe.whitelist()
def create_material_transfer_ashlink(items=None):
    try:
        current_user = frappe.session.user

        # Fetch default warehouse from User Permissions (Source Warehouse)
        user_permissions = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Warehouse", "is_default": 1},
            fields=["for_value"]
        )

        default_warehouses = [perm["for_value"] for perm in user_permissions]
        source_warehouse = default_warehouses[0] if default_warehouses else None

        if not source_warehouse:
            frappe.throw(_("Source warehouse not found. Please set it in User Permissions."))

        # Parse item quantities from JSON string to Python dictionary
        import json
        items_payload = json.loads(items) if isinstance(items, str) else (items or [])

        if not items_payload:
            frappe.throw(_("No items provided for Material Transfer."))

        # Create a Stock Entry (Material Transfer)
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Transfer"
        stock_entry.posting_date = frappe.utils.today()

        for item in items_payload:
            stock_entry.append("items", {
                "item_code": item.get("item_code"),
                "qty": item.get("qty"),
                "uom": item.get("uom"),
                "s_warehouse": source_warehouse,
                "t_warehouse": item.get("warehouse")
            })

        # Insert & submit Stock Entry
        stock_entry.insert(ignore_permissions=True)
        stock_entry.submit()

        return {
            "status": "success",
            "message": _("Material Transfer created successfully."),
            "stock_entry": stock_entry.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Material Transfer Creation Error")
        return {
            "status": "error",
            "message": _("Error creating Material Transfer. Please try again."),
            "error_detail": str(e)
        }
