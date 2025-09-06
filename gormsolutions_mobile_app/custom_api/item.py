import frappe
from erpnext.stock.utils import get_stock_balance

import frappe
from erpnext.stock.utils import get_stock_balance

@frappe.whitelist()
def get_item_details(limit, offset, search=None, user=None):
	"""
	Fetch item details based on filters, user permissions, stock, and UOM information.
	Also includes all UOMs of each item with their related prices.

	Args:
		limit (int): Number of items to fetch.
		offset (int): Offset for pagination.
		search (str, optional): Search keyword for item name.
		user (str, optional): User for fetching POS Profile.

	Returns:
		list: List of item details enriched with stock, price, and UOM information.
	"""
	current_user = frappe.session.user

	# Fetch default warehouse from User Permissions
	user_permissions = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Warehouse"},
		fields=["for_value"]
	)
	default_warehouses = [perm["for_value"] for perm in user_permissions]

	# Use the first warehouse if multiple exist
	default_warehouse = default_warehouses[0] if default_warehouses else None

	if not default_warehouse:
		frappe.throw("Default warehouse not found. Please set it in User Permissions.")

	# Fetch User Permission for Item Groups
	allowed_item_groups = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Item Group"},
		fields=["for_value"]
	)
	allowed_group_names = [group["for_value"] for group in allowed_item_groups]

	# Fetch all child item groups under the allowed groups
	item_groups_to_filter = allowed_group_names[:]
	if allowed_group_names:
		child_groups = frappe.get_all(
			"Item Group",
			filters={"parent_item_group": ["in", allowed_group_names]},
			fields=["name"]
		)
		item_groups_to_filter.extend([group["name"] for group in child_groups])

	# Prepare filters for fetching items
	filters = [
		["disabled", "=", 0],
		["is_sales_item", "=", 1],
		["has_variants", "=", 0],  # Exclude variants
		# ["is_stock_item", "=", 1],
		# ["custom_on_selling_pos", "=", 1],
	]
	if search:
		filters.append(["item_name", "like", f"%{search}%"])
	if item_groups_to_filter:
		filters.append(["item_group", "in", item_groups_to_filter])

	# Fetch items based on the constructed filters
	item_details = frappe.get_all(
		"Item",
		filters=filters,
		fields=["item_code", "item_name", "description", "item_group", "image", "stock_uom"],
		start=offset,
		page_length=limit,
	)

	# Enrich item details with stock, price, and UOM information
	for item in item_details:
		# Get stock balance
		item["stock"] = get_stock_balance(item["item_code"], default_warehouse) or 0

		# Build UOM details: default stock UOM and additional conversion details
		uom_details = [{
			"uom": item["stock_uom"],
			"conversion_factor": 1,
			"price": 0.00  # We will fill the price later
		}]

		# Fetch conversion details for additional UOMs and get the price from Item Price table
		conversion_details = frappe.get_all(
			"UOM Conversion Detail",
			filters={"parent": item["item_code"]},
			fields=["uom", "conversion_factor"]
		)

		# Loop through conversion details to get the price for each UOM
		for conv in conversion_details:
			if conv["uom"] != item["stock_uom"]:
				# Fetch price for the converted UOM from Item Price table
				price = frappe.get_value(
					"Item Price",
					{"item_code": item["item_code"], "selling": 1, "uom": conv["uom"]},
					"price_list_rate",
				) or 0.00
				uom_details.append({
					"uom": conv["uom"],
					"conversion_factor": conv.get("conversion_factor", 1),
					"price": price
				})

		# Now set price for stock UOM
		stock_uom_price = frappe.get_value(
			"Item Price",
			{"item_code": item["item_code"], "selling": 1, "uom": item["stock_uom"]},
			"price_list_rate",
		) or 0.00

		# Update the default UOM price
		uom_details[0]["price"] = stock_uom_price
		item["price"] = stock_uom_price  # Set the default price for the item

		item["uom_details"] = uom_details

		# Fetch stock in other warehouses if permitted
		if frappe.has_permission("Bin", "read", throw=False):
			warehouse_stock = frappe.get_all(
				"Bin",
				filters=[
					["item_code", "=", item["item_code"]],
					["warehouse", "not in", default_warehouses],  # Fixed warehouse filter
				],
				fields=["warehouse", "actual_qty"],
			)
			item["other_warehouse_stock"] = [
				{"warehouse_name": stock["warehouse"], "stock": stock["actual_qty"]}
				for stock in warehouse_stock
			]

	return item_details

@frappe.whitelist(allow_guest = True)
def get_item_details_offline(limit=None,offset=None,search=None):
	
	# filters=[['item_name','like','%'+search+'%']]
	
	item_details = frappe.get_all('Item',
	fields=['item_code', 'item_name','description','stock_uom'],    
	start=offset,
	page_length=limit
	)
	item_stock_details = frappe.get_all('Bin',
	fields=['warehouse', 'actual_qty','item_code'],    
	start=offset,
	page_length=limit
	)
	item_price_details = frappe.get_all('Item Price',
	filters={"selling":1},
	fields=['item_code', 'item_name','price_list_rate','currency'],    
	start=offset,
	page_length=limit
	)
	# return item_details
	return {
		"item_details":item_details,
		"item_stock_details":item_stock_details,
		"item_price_details":item_price_details
	}
	
@frappe.whitelist(allow_guest = True)
def get_item_warehouse_offline(limit=None,offset=None,search=None):
	current_user = frappe.session.user
	# default_warehouse = None

	# Fetch default warehouse exclusively from User Permissions
	user_permissions = frappe.get_all(
		"User Permission",
		filters={"user": current_user},
		fields=["for_value"]
	)
	default_warehouse = [perm["for_value"] for perm in user_permissions]
	
	return user_permissions

@frappe.whitelist()
def get_item_details_barcodes(limit, offset, search=None, user=None):
	"""
	Fetch item details based on filters, user permissions, stock, UOM, price,
	batch/serial number, and barcode information.

	Args:
		limit (int): Number of items to fetch.
		offset (int): Offset for pagination.
		search (str, optional): Search keyword for item name.
		user (str, optional): User for fetching POS Profile.

	Returns:
		list: List of item details enriched with stock, price, UOM, barcode, and batch/serial info.
	"""
	current_user = frappe.session.user

	# Fetch default warehouse from User Permissions
	user_permissions = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Warehouse"},
		fields=["for_value"]
	)
	default_warehouses = [perm["for_value"] for perm in user_permissions]
	default_warehouse = default_warehouses[0] if default_warehouses else None

	if not default_warehouse:
		frappe.throw("Default warehouse not found. Please set it in User Permissions.")

	# Fetch allowed item groups
	allowed_item_groups = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Item Group"},
		fields=["for_value"]
	)
	allowed_group_names = [group["for_value"] for group in allowed_item_groups]

	item_groups_to_filter = allowed_group_names[:]
	if allowed_group_names:
		child_groups = frappe.get_all(
			"Item Group",
			filters={"parent_item_group": ["in", allowed_group_names]},
			fields=["name"]
		)
		item_groups_to_filter.extend([group["name"] for group in child_groups])

	# Prepare filters
	filters = [
		["disabled", "=", 0],
		["is_sales_item", "=", 1],
		["is_stock_item", "=", 1],
	]
	if search:
		filters.append(["item_name", "like", f"%{search}%"])
	if item_groups_to_filter:
		filters.append(["item_group", "in", item_groups_to_filter])

	# Fetch items
	item_details = frappe.get_all(
		"Item",
		filters=filters,
		fields=["item_code", "item_name", "description", "item_group", "image", "stock_uom", "has_batch_no", "has_serial_no"],
		start=offset,
		page_length=limit,
	)

	for item in item_details:
		# Stock balance
		item["stock"] = get_stock_balance(item["item_code"], default_warehouse) or 0

		# Price
		price = frappe.db.get_value("Item Price", {
			"item_code": item["item_code"],
			"selling": 1,
			"price_list": "Standard Selling"
		}, "price_list_rate")
		item["price"] = price or 0

		# UOMs
		item["uoms"] = frappe.get_all(
			"UOM Conversion Detail",
			filters={"parent": item["item_code"]},
			fields=["uom", "conversion_factor"]
		)

		# Barcodes
		barcodes = frappe.get_all(
			"Item Barcode",
			fields=["barcode", "uom"],
			filters={"parent": item["item_code"]}
		)
		item["barcode"] = barcodes[0]["barcode"] if barcodes else ""

		# Batch numbers (if applicable)
		if item.get("has_batch_no"):
			item["batches"] = frappe.get_all(
				"Batch",
				filters={
					"item": item["item_code"],
					"warehouse": default_warehouse,
					"disabled": 0
				},
				fields=["name", "batch_id", "expiry_date"]
			)
		else:
			item["batches"] = []

		# Serial numbers (if applicable)
		if item.get("has_serial_no"):
			item["serial_nos"] = frappe.get_all(
				"Serial No",
				filters={
					"item_code": item["item_code"],
					"warehouse": default_warehouse,
					"status": "Active"
				},
				fields=["name", "serial_no"]
			)
		else:
			item["serial_nos"] = []

	return item_details

@frappe.whitelist()
def get_item_details_roots(limit, offset, search=None, user=None):
	"""
	Fetch item details based on filters, user permissions, stock, and UOM information.
	Also includes all UOMs of each item with their related prices.

	Args:
		limit (int): Number of items to fetch.
		offset (int): Offset for pagination.
		search (str, optional): Search keyword for item name.
		user (str, optional): User for fetching POS Profile.

	Returns:
		list: List of item details enriched with stock, price, and UOM information.
	"""
	current_user = frappe.session.user

	# Fetch default warehouse from User Permissions
	user_permissions = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Warehouse"},
		fields=["for_value"]
	)
	default_warehouses = [perm["for_value"] for perm in user_permissions]
	default_warehouse = default_warehouses[0] if default_warehouses else None

	if not default_warehouse:
		frappe.throw("Default warehouse not found. Please set it in User Permissions.")

	# Fetch User Permission for Item Groups
	allowed_item_groups = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Item Group"},
		fields=["for_value"]
	)
	allowed_group_names = [group["for_value"] for group in allowed_item_groups]

	# Fetch all child item groups under the allowed groups
	item_groups_to_filter = allowed_group_names[:]
	if allowed_group_names:
		child_groups = frappe.get_all(
			"Item Group",
			filters={"parent_item_group": ["in", allowed_group_names]},
			fields=["name"]
		)
		item_groups_to_filter.extend([group["name"] for group in child_groups])

	# Prepare filters for fetching items
	filters = [
		["disabled", "=", 0],
		["is_sales_item", "=", 1],
		# ["is_stock_item", "=", 1],
		["custom_on_selling_pos", "=", 1],
	]
	if search:
		filters.append(["item_name", "like", f"%{search}%"])
	if item_groups_to_filter:
		filters.append(["item_group", "in", item_groups_to_filter])

	# Fetch items
	item_details = frappe.get_all(
		"Item",
		filters=filters,
		fields=["item_code", "item_name", "description", "item_group", "image", "stock_uom", "has_batch_no", "has_serial_no"],
		start=offset,
		page_length=limit,
	)

	for item in item_details:
		# Get stock balance
		item["stock"] = get_stock_balance(item["item_code"], default_warehouse) or 0

		# UOM details
		uom_details = [{
			"uom": item["stock_uom"],
			"conversion_factor": 1,
			"price": 0.00
		}]

		# Conversion UOMs
		conversion_details = frappe.get_all(
			"UOM Conversion Detail",
			filters={"parent": item["item_code"]},
			fields=["uom", "conversion_factor"]
		)

		for conv in conversion_details:
			if conv["uom"] != item["stock_uom"]:
				price = frappe.get_value(
					"Item Price",
					{"item_code": item["item_code"], "selling": 1, "uom": conv["uom"]},
					"price_list_rate"
				) or 0.00
				uom_details.append({
					"uom": conv["uom"],
					"conversion_factor": conv.get("conversion_factor", 1),
					"price": price
				})

		# Price for stock UOM
		stock_uom_price = frappe.get_value(
			"Item Price",
			{"item_code": item["item_code"], "selling": 1, "uom": item["stock_uom"]},
			"price_list_rate"
		) or 0.00
		uom_details[0]["price"] = stock_uom_price
		item["price"] = stock_uom_price
		item["uom_details"] = uom_details

		# Other warehouse stock
		if frappe.has_permission("Bin", "read", throw=False):
			warehouse_stock = frappe.get_all(
				"Bin",
				filters=[
					["item_code", "=", item["item_code"]],
					["warehouse", "not in", default_warehouses],
				],
				fields=["warehouse", "actual_qty"]
			)
			item["other_warehouse_stock"] = [
				{"warehouse_name": stock["warehouse"], "stock": stock["actual_qty"]}
				for stock in warehouse_stock
			]

		# Barcodes
		barcodes = frappe.get_all(
			"Item Barcode",
			fields=["barcode", "uom"],
			filters={"parent": item["item_code"]}
		)
		item["barcode"] = barcodes[0]["barcode"] if barcodes else ""

		# Batches
		if item.get("has_batch_no"):
			item["batches"] = frappe.get_all(
				"Batch",
				filters={
					"item": item["item_code"],
					"warehouse": default_warehouse,
					"disabled": 0
				},
				fields=["name", "batch_id", "expiry_date"]
			)
		else:
			item["batches"] = []

		# Serial Numbers
		if item.get("has_serial_no"):
			item["serial_nos"] = frappe.get_all(
				"Serial No",
				filters={
					"item_code": item["item_code"],
					"warehouse": default_warehouse,
					"status": "Active"
				},
				fields=["name", "serial_no"]
			)
		else:
			item["serial_nos"] = []

	return item_details

import frappe
from erpnext.stock.utils import get_stock_balance

@frappe.whitelist()
def get_item_details_gen7(limit, offset, search=None, user=None):
	"""
	Fetch item details based on filters, user permissions, and stock.
	Only returns item stock and price (no UOM array).

	Args:
		limit (int): Number of items to fetch.
		offset (int): Offset for pagination.
		search (str, optional): Search keyword for item name.
		user (str, optional): User for fetching POS Profile.

	Returns:
		list: List of item details enriched with stock and price.
	"""
	current_user = frappe.session.user

	# Fetch default warehouse from User Permissions
	user_permissions = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Warehouse","is_default":1},
		fields=["for_value"]
	)
	default_warehouses = [perm["for_value"] for perm in user_permissions]
	default_warehouse = default_warehouses[0] if default_warehouses else None

	if not default_warehouse:
		frappe.throw("Default warehouse not found. Please set it in User Permissions.")

	# Fetch allowed item groups
	allowed_item_groups = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Item Group"},
		fields=["for_value"]
	)
	allowed_group_names = [group["for_value"] for group in allowed_item_groups]

	# Include child groups of allowed item groups
	item_groups_to_filter = allowed_group_names[:]
	if allowed_group_names:
		child_groups = frappe.get_all(
			"Item Group",
			filters={"parent_item_group": ["in", allowed_group_names]},
			fields=["name"]
		)
		item_groups_to_filter.extend([group["name"] for group in child_groups])

	# Build item filters
	filters = [
		["disabled", "=", 0],
		["is_sales_item", "=", 1],
		["has_variants", "=", 0],
	]
	if search:
		filters.append(["item_name", "like", f"%{search}%"])
	if item_groups_to_filter:
		filters.append(["item_group", "in", item_groups_to_filter])

	# Fetch item data
	item_details = frappe.get_all(
		"Item",
		filters=filters,
		fields=["item_code", "item_name", "description", "item_group", "image", "stock_uom"],
		start=offset,
		page_length=limit,
	)

	# Add stock and price info
	for item in item_details:
		# Stock balance in default warehouse
		item["stock"] = get_stock_balance(item["item_code"], default_warehouse) or 0

		# Price for stock UOM
		item["price"] = frappe.get_value(
			"Item Price",
			{"item_code": item["item_code"], "selling": 1, "uom": item["stock_uom"]},
			"price_list_rate",
		) or 0.00

		# Optional: other warehouses stock info
		if frappe.has_permission("Bin", "read", throw=False):
			warehouse_stock = frappe.get_all(
				"Bin",
				filters=[
					["item_code", "=", item["item_code"]],
					["warehouse", "not in", default_warehouses],
				],
				fields=["warehouse", "actual_qty"],
			)
			item["other_warehouse_stock"] = [
				{"warehouse_name": stock["warehouse"], "stock": stock["actual_qty"]}
				for stock in warehouse_stock
			]

	return item_details

@frappe.whitelist()
def get_item_details_ashlink(limit, offset, search=None, user=None):
	"""
	Fetch item details based on filters, user permissions, stock, and UOM information.
	Also includes all UOMs of each item with their related prices.

	Args:
		limit (int): Number of items to fetch.
		offset (int): Offset for pagination.
		search (str, optional): Search keyword for item name.
		user (str, optional): User for fetching POS Profile.

	Returns:
		list: List of item details enriched with stock, price, and UOM information.
	"""
	current_user = frappe.session.user

	# Fetch default warehouse from User Permissions
	user_permissions = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Warehouse","is_default":1},
		fields=["for_value"]
	)
	default_warehouses = [perm["for_value"] for perm in user_permissions]
	default_warehouse = default_warehouses[0] if default_warehouses else None

	if not default_warehouse:
		frappe.throw("Default warehouse not found. Please set it in User Permissions.")

	# Fetch User Permission for Item Groups
	allowed_item_groups = frappe.get_all(
		"User Permission",
		filters={"user": current_user, "allow": "Item Group"},
		fields=["for_value"]
	)
	allowed_group_names = [group["for_value"] for group in allowed_item_groups]

	# Fetch all child item groups under the allowed groups
	item_groups_to_filter = allowed_group_names[:]
	if allowed_group_names:
		child_groups = frappe.get_all(
			"Item Group",
			filters={"parent_item_group": ["in", allowed_group_names]},
			fields=["name"]
		)
		item_groups_to_filter.extend([group["name"] for group in child_groups])

	# Prepare filters for fetching items
	filters = [
		["disabled", "=", 0],
		["is_sales_item", "=", 1],
		["has_variants", "=", 0],
		# ["is_stock_item", "=", 1],
		# ["custom_on_selling_pos", "=", 1],
	]
	if search:
		filters.append(["item_name", "like", f"%{search}%"])
	if item_groups_to_filter:
		filters.append(["item_group", "in", item_groups_to_filter])

	# Fetch items
	item_details = frappe.get_all(
		"Item",
		filters=filters,
		fields=["item_code", "item_name", "description", "item_group", "image", "stock_uom", "has_batch_no", "has_serial_no"],
		start=offset,
		page_length=limit,
	)

	for item in item_details:
		# Get stock balance
		item["stock"] = get_stock_balance(item["item_code"], default_warehouse) or 0

		# UOM details
		uom_details = [{
			"uom": item["stock_uom"],
			"conversion_factor": 1,
			"price": 0.00
		}]

		# Conversion UOMs
		conversion_details = frappe.get_all(
			"UOM Conversion Detail",
			filters={"parent": item["item_code"]},
			fields=["uom", "conversion_factor"]
		)

		for conv in conversion_details:
			if conv["uom"] != item["stock_uom"]:
				price = frappe.get_value(
					"Item Price",
					{"item_code": item["item_code"], "selling": 1, "uom": conv["uom"]},
					"price_list_rate"
				) or 0.00
				uom_details.append({
					"uom": conv["uom"],
					"conversion_factor": conv.get("conversion_factor", 1),
					"price": price
				})

		# Price for stock UOM
		stock_uom_price = frappe.get_value(
			"Item Price",
			{"item_code": item["item_code"], "selling": 1, "uom": item["stock_uom"]},
			"price_list_rate"
		) or 0.00
		uom_details[0]["price"] = stock_uom_price
		item["price"] = stock_uom_price
		item["uom_details"] = uom_details

		# Other warehouse stock
		if frappe.has_permission("Bin", "read", throw=False):
			warehouse_stock = frappe.get_all(
				"Bin",
				filters=[
					["item_code", "=", item["item_code"]],
					["warehouse", "not in", default_warehouses],
				],
				fields=["warehouse", "actual_qty"]
			)
			item["other_warehouse_stock"] = [
				{"warehouse_name": stock["warehouse"], "stock": stock["actual_qty"]}
				for stock in warehouse_stock
			]

		# Barcodes
		barcodes = frappe.get_all(
			"Item Barcode",
			fields=["barcode", "uom"],
			filters={"parent": item["item_code"]}
		)
		item["barcode"] = barcodes[0]["barcode"] if barcodes else ""

		# Batches
		if item.get("has_batch_no"):
			item["batches"] = frappe.get_all(
				"Batch",
				filters={
					"item": item["item_code"],
					"warehouse": default_warehouse,
					"disabled": 0
				},
				fields=["name", "batch_id", "expiry_date"]
			)
		else:
			item["batches"] = []

		# Serial Numbers
		if item.get("has_serial_no"):
			item["serial_nos"] = frappe.get_all(
				"Serial No",
				filters={
					"item_code": item["item_code"],
					"warehouse": default_warehouse,
					"status": "Active"
				},
				fields=["name", "serial_no"]
			)
		else:
			item["serial_nos"] = []

	return item_details

import frappe
from erpnext.stock.utils import get_stock_balance

import frappe

@frappe.whitelist()
def get_item_details_ashlink_damage(limit, offset, search=None, user=None):
	"""
	Fetch ONLY items that exist in Bin for Damaged Stores - AEL.
	Includes stock, price, UOMs, barcodes, batches, and serials.
	"""
	default_warehouse = "Damaged Stores - AEL"

	# 🔹 Step 1: Get item codes that have Bin entries in this warehouse
	bin_filters = {"warehouse": default_warehouse}
	if search:
		# If searching, join with Item table later
		pass

	bin_items = frappe.get_all(
		"Bin",
		filters=bin_filters,
		fields=["item_code", "actual_qty"],
		start=offset,
		page_length=limit
	)

	if not bin_items:
		return []  # No items in that warehouse

	# Get all item codes from Bin
	item_codes = [b["item_code"] for b in bin_items]
	stock_map = {b["item_code"]: b["actual_qty"] for b in bin_items}

	# 🔹 Step 2: Get item details for those item codes
	item_filters = [["item_code", "in", item_codes]]
	if search:
		item_filters.append(["item_name", "like", f"%{search}%"])

	items = frappe.get_all(
		"Item",
		filters=item_filters,
		fields=[
			"item_code", "item_name", "description", "item_group",
			"image", "stock_uom", "has_batch_no", "has_serial_no"
		],
	)

	results = []
	for item in items:
		# Set stock from our Bin stock map
		item["stock"] = stock_map.get(item["item_code"], 0)

		# UOM details (start with stock UOM)
		uom_details = [{
			"uom": item["stock_uom"],
			"conversion_factor": 1,
			"price": 0.00
		}]

		# Conversion UOMs
		conversions = frappe.get_all(
			"UOM Conversion Detail",
			filters={"parent": item["item_code"]},
			fields=["uom", "conversion_factor"]
		)
		for conv in conversions:
			price = frappe.get_value(
				"Item Price",
				{"item_code": item["item_code"], "selling": 1, "uom": conv["uom"]},
				"price_list_rate"
			) or 0.00
			uom_details.append({
				"uom": conv["uom"],
				"conversion_factor": conv.get("conversion_factor", 1),
				"price": price
			})

		# Price for stock UOM
		stock_price = frappe.get_value(
			"Item Price",
			{"item_code": item["item_code"], "selling": 1, "uom": item["stock_uom"]},
			"price_list_rate"
		) or 0.00
		uom_details[0]["price"] = stock_price
		item["price"] = stock_price
		item["uom_details"] = uom_details

		# Barcodes
		barcodes = frappe.get_all(
			"Item Barcode",
			fields=["barcode", "uom"],
			filters={"parent": item["item_code"]}
		)
		item["barcode"] = barcodes[0]["barcode"] if barcodes else ""

		# Batches
		item["batches"] = frappe.get_all(
			"Batch",
			filters={"item": item["item_code"], "warehouse": default_warehouse, "disabled": 0},
			fields=["name", "batch_id", "expiry_date"]
		) if item.get("has_batch_no") else []

		# Serial Numbers
		item["serial_nos"] = frappe.get_all(
			"Serial No",
			filters={"item_code": item["item_code"], "warehouse": default_warehouse, "status": "Active"},
			fields=["name", "serial_no"]
		) if item.get("has_serial_no") else []

		results.append(item)

	return results

@frappe.whitelist()
def get_item_details_ashlink_stockreturns(limit, offset, warehouse, search=None, user=None):
    """
    Fetch ONLY items that exist in Bin for the given warehouse.
    Includes stock, price, UOMs, barcodes, batches, and serials.
    
    Args:
        limit (int): Number of records to fetch
        offset (int): Starting index
        warehouse (str): Warehouse name (e.g., "Damaged Stores - AEL")
        search (str, optional): Search keyword for item_name
        user (str, optional): Current user (not enforced yet)
    """
    if not warehouse:
        frappe.throw("Warehouse is required")

    # 🔹 Step 1: Get item codes that have Bin entries in this warehouse
    bin_filters = {"warehouse": warehouse}

    bin_items = frappe.get_all(
        "Bin",
        filters=bin_filters,
        fields=["item_code", "actual_qty"],
        start=offset,
        page_length=limit
    )

    if not bin_items:
        return []  # No items in that warehouse

    # Get all item codes from Bin
    item_codes = [b["item_code"] for b in bin_items]
    stock_map = {b["item_code"]: b["actual_qty"] for b in bin_items}

    # 🔹 Step 2: Get item details for those item codes
    item_filters = [["item_code", "in", item_codes]]
    if search:
        item_filters.append(["item_name", "like", f"%{search}%"])

    items = frappe.get_all(
        "Item",
        filters=item_filters,
        fields=[
            "item_code", "item_name", "description", "item_group",
            "image", "stock_uom", "has_batch_no", "has_serial_no"
        ],
    )

    results = []
    for item in items:
        # Set stock from our Bin stock map
        item["stock"] = stock_map.get(item["item_code"], 0)

        # UOM details (start with stock UOM)
        uom_details = [{
            "uom": item["stock_uom"],
            "conversion_factor": 1,
            "price": 0.00
        }]

        # Conversion UOMs
        conversions = frappe.get_all(
            "UOM Conversion Detail",
            filters={"parent": item["item_code"]},
            fields=["uom", "conversion_factor"]
        )
        for conv in conversions:
            price = frappe.get_value(
                "Item Price",
                {"item_code": item["item_code"], "selling": 1, "uom": conv["uom"]},
                "price_list_rate"
            ) or 0.00
            uom_details.append({
                "uom": conv["uom"],
                "conversion_factor": conv.get("conversion_factor", 1),
                "price": price
            })

        # Price for stock UOM
        stock_price = frappe.get_value(
            "Item Price",
            {"item_code": item["item_code"], "selling": 1, "uom": item["stock_uom"]},
            "price_list_rate"
        ) or 0.00
        uom_details[0]["price"] = stock_price
        item["price"] = stock_price
        item["uom_details"] = uom_details

        # Barcodes
        barcodes = frappe.get_all(
            "Item Barcode",
            fields=["barcode", "uom"],
            filters={"parent": item["item_code"]}
        )
        item["barcode"] = barcodes[0]["barcode"] if barcodes else ""

        # Batches
        item["batches"] = frappe.get_all(
            "Batch",
            filters={"item": item["item_code"], "warehouse": warehouse, "disabled": 0},
            fields=["name", "batch_id", "expiry_date"]
        ) if item.get("has_batch_no") else []

        # Serial Numbers
        item["serial_nos"] = frappe.get_all(
            "Serial No",
            filters={"item_code": item["item_code"], "warehouse": warehouse, "status": "Active"},
            fields=["name", "serial_no"]
        ) if item.get("has_serial_no") else []

        results.append(item)

    return results

import frappe
@frappe.whitelist()
def get_item_details_ashlink_buying(limit, offset, search=None, user=None):
    current_user = frappe.session.user

    # Fetch default warehouse from User Permissions
    user_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Warehouse", "is_default": 1},
        fields=["for_value"]
    )
    default_warehouses = [perm["for_value"] for perm in user_permissions]
    default_warehouse = default_warehouses[0] if default_warehouses else None

    if not default_warehouse:
        frappe.throw("Default warehouse not found. Please set it in User Permissions.")

    # Fetch User Permission for Item Groups
    allowed_item_groups = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Item Group"},
        fields=["for_value"]
    )
    allowed_group_names = [group["for_value"] for group in allowed_item_groups]

    item_groups_to_filter = allowed_group_names[:]
    if allowed_group_names:
        child_groups = frappe.get_all(
            "Item Group",
            filters={"parent_item_group": ["in", allowed_group_names]},
            fields=["name"]
        )
        item_groups_to_filter.extend([group["name"] for group in child_groups])

    # Prepare filters for fetching items
    filters = [
        ["disabled", "=", 0],
        ["is_sales_item", "=", 1],
        ["has_variants", "=", 0],
    ]
    if search:
        filters.append(["item_name", "like", f"%{search}%"])
    if item_groups_to_filter:
        filters.append(["item_group", "in", item_groups_to_filter])

    # Fetch items
    item_details = frappe.get_all(
        "Item",
        filters=filters,
        fields=[
            "item_code",
            "item_name",
            "description",
            "item_group",
            "image",
            "stock_uom",
            "has_batch_no",
            "has_serial_no",
            "valuation_rate"
        ],
        start=offset,
        page_length=limit,
    )

    for item in item_details:
        # Stock balance
        item["stock"] = get_stock_balance(item["item_code"], default_warehouse) or 0

        # Cost price from valuation_rate or latest buying price
        cost_price = item.get("valuation_rate") or 0.00
        if not cost_price:
            latest_buying_price = frappe.get_all(
                "Item Price",
                filters={"item_code": item["item_code"], "buying": 1},
                fields=["price_list_rate"],
                order_by="modified desc",
                limit=1
            )
            cost_price = latest_buying_price[0]["price_list_rate"] if latest_buying_price else 0.00
        item["cost_price"] = cost_price

        # UOM details (all conversion UOMs)
        uom_details = []

        # Get all Item Prices for buying
        item_prices = frappe.get_all(
            "Item Price",
            filters={"item_code": item["item_code"], "buying": 1},
            fields=["uom", "price_list_rate"]
        )
        price_map = {ip["uom"]: ip["price_list_rate"] for ip in item_prices}

        # Stock UOM first
        uom_details.append({
            "uom": item["stock_uom"],
            "conversion_factor": 1,
            "price": price_map.get(item["stock_uom"], 0.0),
            "cost_per_uom": price_map.get(item["stock_uom"], 0.0)
        })
        item["price"] = price_map.get(item["stock_uom"], 0.0)

        # Conversion UOMs
        conversion_details = frappe.get_all(
            "UOM Conversion Detail",
            filters={"parent": item["item_code"]},
            fields=["uom", "conversion_factor"]
        )
        for conv in conversion_details:
            if conv["uom"] != item["stock_uom"]:
                uom_details.append({
                    "uom": conv["uom"],
                    "conversion_factor": conv.get("conversion_factor", 1),
                    "price": price_map.get(conv["uom"], 0.0),
                    "cost_per_uom": price_map.get(conv["uom"], 0.0)
                })

        item["uom_details"] = uom_details

        # Other warehouse stock
        if frappe.has_permission("Bin", "read", throw=False):
            warehouse_stock = frappe.get_all(
                "Bin",
                filters=[
                    ["item_code", "=", item["item_code"]],
                    ["warehouse", "not in", default_warehouses],
                ],
                fields=["warehouse", "actual_qty", "valuation_rate"]
            )
            item["other_warehouse_stock"] = [
                {
                    "warehouse_name": stock["warehouse"],
                    "stock": stock["actual_qty"],
                    "cost_price": stock["valuation_rate"] or cost_price,
                    "cost_per_uom": stock["valuation_rate"] or cost_price
                }
                for stock in warehouse_stock
            ]

        # Barcodes
        barcodes = frappe.get_all(
            "Item Barcode",
            fields=["barcode", "uom"],
            filters={"parent": item["item_code"]}
        )
        item["barcode"] = barcodes[0]["barcode"] if barcodes else ""

        # Batches
        if item.get("has_batch_no"):
            item["batches"] = frappe.get_all(
                "Batch",
                filters={
                    "item": item["item_code"],
                    "warehouse": default_warehouse,
                    "disabled": 0
                },
                fields=["name", "batch_id", "expiry_date"]
            )
        else:
            item["batches"] = []

        # Serial Numbers
        if item.get("has_serial_no"):
            item["serial_nos"] = frappe.get_all(
                "Serial No",
                filters={
                    "item_code": item["item_code"],
                    "warehouse": default_warehouse,
                    "status": "Active"
                },
                fields=["name", "serial_no"]
            )
        else:
            item["serial_nos"] = []

    return item_details
