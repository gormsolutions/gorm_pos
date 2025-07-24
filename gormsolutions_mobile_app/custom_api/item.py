import frappe
from erpnext.stock.utils import get_stock_balance
from frappe import throw, msgprint, _

@frappe.whitelist()
def get_gasitems_details(limit, offset, search=None, user=None):
    """
    Fetch item details based on filters, user permissions, and stock information.
    """
    current_user = frappe.session.user

    # Fetch all warehouses from User Permissions
    user_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Warehouse"},
        fields=["for_value"]
    )
    allowed_warehouses = [perm["for_value"] for perm in user_permissions]
    
    if not allowed_warehouses:
        frappe.throw(_("No warehouses found in User Permissions. Please set them."))
    
    # Fetch allowed Item Groups
    allowed_item_groups = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Item Group"},
        fields=["for_value"]
    )
    allowed_group_names = [group["for_value"] for group in allowed_item_groups]

    # Fetch allowed Price List
    price_list_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Price List","is_default":1},
        fields=["for_value"]
    )
    price_lists = [perm["for_value"] for perm in price_list_permissions]
    
    if not price_lists:
        frappe.throw(_("No price list found. Please set it in User Permissions."))
    price_list = price_lists[0]

    # Fetch all child item groups under allowed groups
    item_groups_to_filter = allowed_group_names[:]
    if allowed_group_names:
        child_groups = frappe.get_all(
            "Item Group",
            filters={"parent_item_group": ["in", allowed_group_names]},
            fields=["name"]
        )
        item_groups_to_filter.extend([group["name"] for group in child_groups])

    # Prepare filters for fetching items
    # filters = [["disabled", "=", 0, "custom_dissable_on_mobile", "=", 1]]
    filters = [
    ["disabled", "=", 0],
    ["custom_dissable_on_mobile", "=", 0]
    
    ]

    if search:
        filters.append(["item_name", "like", f"%{search}%"])
    if item_groups_to_filter:
        filters.append(["item_group", "in", item_groups_to_filter])

    # Fetch items based on filters
    item_details = frappe.get_all(
        "Item",
        filters=filters,
        fields=["item_code", "item_name", "description", "image", "item_group", "stock_uom", "custom_promotion_amount", "custom_on_promotion"],
        start=offset,
        page_length=limit,
    )

    # Enrich item details with stock and price information
    for item in item_details:
        warehouse_stock = []
        
        if "empty" in item["item_code"].lower():
            stock_total = 0  # Reset stock total for 'empty' items
            for warehouse in allowed_warehouses:
                if "empty" in warehouse.lower():  # Only pick warehouses containing 'Empty'
                    stock_balance = get_stock_balance(item["item_code"], warehouse) or 0.00
                    stock_total = stock_balance  # Do not aggregate, just set the stock
                    warehouse_stock.append({
                        "warehouse_name": warehouse,
                        "stock": stock_balance
                    })
        else:
            stock_total = 0
            for warehouse in allowed_warehouses:
                stock_balance = get_stock_balance(item["item_code"], warehouse) or 0.00
                stock_total += stock_balance
                warehouse_stock.append({
                    "warehouse_name": warehouse,
                    "stock": stock_balance
                })
        
        item["stock"] = stock_total
        item["other_warehouse_stock"] = warehouse_stock

        # Get item price from the price list
        item["price"] = frappe.get_value(
            "Item Price",
            {"item_code": item["item_code"], "selling": 1, "price_list": price_list},
            "price_list_rate"
        ) or 0.00

    return item_details

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

    # Fetch allowed Price List
    price_list_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Price List", "is_default": 1},
        fields=["for_value"]
    )
    price_lists = [perm["for_value"] for perm in price_list_permissions]
    
    if not price_lists:
        frappe.throw(_("No price list found. Please set it in User Permissions."))
    price_list = price_lists[0]

    # Fetch default warehouse from User Permissions
    user_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Warehouse"},
        fields=["for_value"]
    )
    default_warehouses = [perm["for_value"] for perm in user_permissions]
    default_warehouse = default_warehouses[0] if default_warehouses else None

    if not default_warehouse:
        frappe.throw(_("Default warehouse not found. Please set it in User Permissions."))

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
            "price": 0.00
        }]

        # Fetch conversion details
        conversion_details = frappe.get_all(
            "UOM Conversion Detail",
            filters={"parent": item["item_code"]},
            fields=["uom", "conversion_factor"]
        )

        # Loop through conversion details to get price
        for conv in conversion_details:
            if conv["uom"] != item["stock_uom"]:
                price = frappe.get_value(
                    "Item Price",
                    {
                        "item_code": item["item_code"],
                        "selling": 1,
                        "price_list": price_list,
                        "uom": conv["uom"]
                    },
                    "price_list_rate"
                ) or 0.00
                uom_details.append({
                    "uom": conv["uom"],
                    "conversion_factor": conv["conversion_factor"],
                    "price": price
                })

        # Price for stock UOM
        stock_uom_price = frappe.get_value(
            "Item Price",
            {
                "item_code": item["item_code"],
                "selling": 1,
                "price_list": price_list,
                "uom": item["stock_uom"]
            },
            "price_list_rate"
        ) or 0.00

        uom_details[0]["price"] = stock_uom_price
        item["price"] = stock_uom_price
        item["uom_details"] = uom_details

        # Stock in other warehouses if permitted
        if frappe.has_permission("Bin", "read", throw=False):
            warehouse_stock = frappe.get_all(
                "Bin",
                filters=[
                    ["item_code", "=", item["item_code"]],
                    ["warehouse", "not in", default_warehouses]
                ],
                fields=["warehouse", "actual_qty"]
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
def get_gasitems_buyingrates(limit, offset, search=None, user=None):
    """
    Fetch item details based on filters, user permissions, and stock information.
    """
    current_user = frappe.session.user

    # Fetch all warehouses from User Permissions
    user_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Warehouse"},
        fields=["for_value"]
    )
    allowed_warehouses = [perm["for_value"] for perm in user_permissions]
    
    if not allowed_warehouses:
        frappe.throw(_("No warehouses found in User Permissions. Please set them."))
    
    # Fetch allowed Item Groups
    allowed_item_groups = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Item Group"},
        fields=["for_value"]
    )
    allowed_group_names = [group["for_value"] for group in allowed_item_groups]

    # Fetch allowed Price List
    price_list_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Price List","is_default":0},
        fields=["for_value"]
    )
    price_lists = [perm["for_value"] for perm in price_list_permissions]
    
    if not price_lists:
        frappe.throw(_("No price list found. Please set it in User Permissions."))
    price_list = price_lists[0]

    # Fetch all child item groups under allowed groups
    item_groups_to_filter = allowed_group_names[:]
    if allowed_group_names:
        child_groups = frappe.get_all(
            "Item Group",
            filters={"parent_item_group": ["in", allowed_group_names]},
            fields=["name"]
        )
        item_groups_to_filter.extend([group["name"] for group in child_groups])

    # Prepare filters for fetching items
    filters = [["disabled", "=", 0]]
    if search:
        filters.append(["item_name", "like", f"%{search}%"])
    if item_groups_to_filter:
        filters.append(["item_group", "in", item_groups_to_filter])

    # Fetch items based on filters
    item_details = frappe.get_all(
        "Item",
        filters=filters,
        fields=["item_code", "item_name", "description", "image", "item_group", "stock_uom", "custom_promotion_amount", "custom_on_promotion"],
        start=offset,
        page_length=limit,
    )

    # Enrich item details with stock and price information
    for item in item_details:
        warehouse_stock = []
        
        if "empty" in item["item_code"].lower():
            stock_total = 0  # Reset stock total for 'empty' items
            for warehouse in allowed_warehouses:
                if "empty" in warehouse.lower():  # Only pick warehouses containing 'Empty'
                    stock_balance = get_stock_balance(item["item_code"], warehouse) or 0.00
                    stock_total = stock_balance  # Do not aggregate, just set the stock
                    warehouse_stock.append({
                        "warehouse_name": warehouse,
                        "stock": stock_balance
                    })
        else:
            stock_total = 0
            for warehouse in allowed_warehouses:
                stock_balance = get_stock_balance(item["item_code"], warehouse) or 0.00
                stock_total += stock_balance
                warehouse_stock.append({
                    "warehouse_name": warehouse,
                    "stock": stock_balance
                })
        
        item["stock"] = stock_total
        item["other_warehouse_stock"] = warehouse_stock

        # Get item price from the price list
        item["price"] = frappe.get_value(
            "Item Price",
            {"item_code": item["item_code"], "buying": 1, "price_list": price_list},
            "price_list_rate"
        ) or 0.00

    return item_details


import frappe
from frappe import _
from erpnext.stock.utils import get_stock_balance

@frappe.whitelist()
def get_gasitems_details_buddle(limit, offset, search=None, user=None):
    current_user = frappe.session.user

    # Get allowed warehouses
    user_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Warehouse"},
        fields=["for_value"]
    )
    allowed_warehouses = [perm["for_value"] for perm in user_permissions]

    if not allowed_warehouses:
        frappe.throw(_("No warehouses found in User Permissions. Please set them."))

    # Get allowed item groups
    allowed_item_groups = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Item Group"},
        fields=["for_value"]
    )
    allowed_group_names = [group["for_value"] for group in allowed_item_groups]

    # Get allowed price list
    price_list_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Price List", "is_default": 1},
        fields=["for_value"]
    )
    price_lists = [perm["for_value"] for perm in price_list_permissions]

    if not price_lists:
        frappe.throw(_("No price list found. Please set it in User Permissions."))

    price_list = price_lists[0]

    # Build item group filter
    item_groups_to_filter = allowed_group_names[:]
    if allowed_group_names:
        child_groups = frappe.get_all(
            "Item Group",
            filters={"parent_item_group": ["in", allowed_group_names]},
            fields=["name"]
        )
        item_groups_to_filter.extend([group["name"] for group in child_groups])

    # Item filters
    filters = [["disabled", "=", 0], ["custom_dissable_on_mobile", "=", 0]]
    if search:
        filters.append(["item_name", "like", f"%{search}%"])
    if item_groups_to_filter:
        filters.append(["item_group", "in", item_groups_to_filter])

    # Fetch items
    item_details = frappe.get_all(
        "Item",
        filters=filters,
        fields=[
            "item_code", "item_name", "description", "image",
            "item_group", "stock_uom", "custom_promotion_amount", "custom_on_promotion"
        ],
        start=offset,
        page_length=limit,
    )

    for i, item in enumerate(item_details):
        bundle_name = frappe.db.get_value("Product Bundle", {"new_item_code": item["item_code"]})

        if bundle_name:
            # It's a bundle — fetch enriched bundle_items
            bundle_items_raw = frappe.get_all(
                "Product Bundle Item",
                filters={"parent": bundle_name},
                fields=["item_code"]
            )
            bundle_items = []

            for b in bundle_items_raw:
                component_stock = 0
                warehouses = []

                for warehouse in allowed_warehouses:
                    item_lower = b["item_code"].lower()
                    warehouse_lower = warehouse.lower()

                    if "gas" in item_lower and "gas" not in warehouse_lower:
                        continue
                    if "empty" in item_lower and "empty" not in warehouse_lower:
                        continue

                    stock_balance = frappe.get_cached_value(
                        "Bin",
                        {"item_code": b["item_code"], "warehouse": warehouse},
                        "actual_qty"
                    ) or 0.00

                    component_stock += stock_balance
                    warehouses.append({
                        "warehouse_name": warehouse,
                        "stock": stock_balance
                    })

                # Get price for bundled item
                price = frappe.get_value(
                    "Item Price",
                    {
                        "item_code": b["item_code"],
                        "selling": 1,
                        "price_list": price_list
                    },
                    "price_list_rate"
                ) or 0.00

                bundle_items.append({
                    "item_code": b["item_code"],
                    "stock": component_stock,
                    "warehouses": warehouses,
                    "price": price
                })

            item["bundle_items"] = bundle_items

            # Get bundled item price (from item_price)
            item_price = frappe.get_value(
                "Item Price",
                {
                    "item_code": item["item_code"],
                    "selling": 1,
                    "price_list": price_list,
                    "uom": item["stock_uom"]
                },
                "price_list_rate"
            ) or 0.00

            item["price"] = item_price

        else:
            # It’s a normal item — add stock and UOM info
            stock_total = 0
            warehouse_stock = []

            for warehouse in allowed_warehouses:
                item_lower = item["item_code"].lower()
                warehouse_lower = warehouse.lower()

                if "empty" in item_lower and "empty" not in warehouse_lower:
                    continue
                if "empty" not in item_lower and "gas" in item_lower and "gas" not in warehouse_lower:
                    continue

                stock_balance = get_stock_balance(item["item_code"], warehouse) or 0.00
                stock_total += stock_balance
                warehouse_stock.append({
                    "warehouse_name": warehouse,
                    "stock": stock_balance
                })

            item["stock"] = stock_total
            item["other_warehouse_stock"] = warehouse_stock

            # ---------- UOM + PRICE ENRICHMENT START ----------
            uom_details = [{
                "uom": item["stock_uom"],
                "conversion_factor": 1,
                "price": 0.00
            }]

            # Fetch alternative UOMs
            conversion_details = frappe.get_all(
                "UOM Conversion Detail",
                filters={"parent": item["item_code"]},
                fields=["uom", "conversion_factor"]
            )

            for conv in conversion_details:
                if conv["uom"] != item["stock_uom"]:
                    price = frappe.get_value(
                        "Item Price",
                        {
                            "item_code": item["item_code"],
                            "selling": 1,
                            "price_list": price_list,
                            "uom": conv["uom"]
                        },
                        "price_list_rate"
                    ) or 0.00

                    uom_details.append({
                        "uom": conv["uom"],
                        "conversion_factor": conv["conversion_factor"],
                        "price": price
                    })

            # Get stock UOM price
            stock_uom_price = frappe.get_value(
                "Item Price",
                {
                    "item_code": item["item_code"],
                    "selling": 1,
                    "price_list": price_list,
                    "uom": item["stock_uom"]
                },
                "price_list_rate"
            ) or 0.00

            uom_details[0]["price"] = stock_uom_price
            item["price"] = stock_uom_price
            item["uom_details"] = uom_details
            # ---------- UOM + PRICE ENRICHMENT END ----------

        # === INSERT original_price after custom_on_promotion ===
        item_ordered = {}
        for key in item:
            item_ordered[key] = item[key]
            if key == "custom_on_promotion":
                original_price = frappe.get_value(
                    "Item Price",
                    {
                        "item_code": item["item_code"],
                        "selling": 1,
                        "price_list": price_list,
                        "uom": item["stock_uom"]
                    },
                    "price_list_rate"
                ) or 0.00
                item_ordered["original_price"] = original_price if item["custom_on_promotion"] else 0.00

        item_details[i] = item_ordered

    return item_details
