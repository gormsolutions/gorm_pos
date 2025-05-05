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
        ["is_stock_item", "=", 1],
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
