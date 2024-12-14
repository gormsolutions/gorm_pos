import frappe
from erpnext.stock.utils import get_stock_balance

@frappe.whitelist()
def get_item_details(limit, offset, search=None, user=None):
    """
    Fetch item details based on filters, user permissions, and stock information.

    Args:
        limit (int): Number of items to fetch.
        offset (int): Offset for pagination.
        search (str, optional): Search keyword for item name.
        user (str, optional): User for fetching POS Profile.

    Returns:
        list: List of item details with stock and price information.
    """
    current_user = frappe.session.user

    # Fetch default warehouse from User Permissions
    user_permissions = frappe.get_all(
        "User Permission",
        filters={"user": current_user, "allow": "Warehouse"},
        fields=["for_value"]
    )
    default_warehouse = [perm["for_value"] for perm in user_permissions]
    if not default_warehouse:
        frappe.throw("Default warehouse not found. Please set it in User Permissions.")

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
        filters={"user": current_user, "allow": "Price List"},
        fields=["for_value"]
    )
    price_list = [perm["for_value"] for perm in price_list_permissions]
    if not price_list:
        frappe.throw("No price list found. Please set it in User Permissions.")

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
    filters = [
        ["disabled", "=", 0],
        ["is_sales_item", "=", 1],
        ["is_stock_item", "=", 1],
    ]
    if search:
        filters.append(["item_name", "like", f"%{search}%"])
    if item_groups_to_filter:
        filters.append(["item_group", "in", item_groups_to_filter])

    # Fetch items based on filters
    item_details = frappe.get_all(
        "Item",
        filters=filters,
        fields=["item_code", "item_name", "description", "item_group", "stock_uom"],
        start=offset,
        page_length=limit,
    )

    # Enrich item details with stock and price information
    for item in item_details:
        try:
            item["stock"] = get_stock_balance(item["item_code"], default_warehouse)
        except Exception:
            item["stock"] = 0.00

        item["price"] = frappe.get_value(
            "Item Price",
            {"item_code": item["item_code"], "selling": 1, "price_list": price_list[0]},
            "price_list_rate"
        ) or 0.00

        # Fetch stock in other warehouses if permitted
        if frappe.has_permission("Bin", ptype="read", throw=False):
            warehouse_stock = frappe.get_all(
                "Bin",
                filters=[
                    ["item_code", "=", item["item_code"]],
                    ["warehouse", "!=", default_warehouse],
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