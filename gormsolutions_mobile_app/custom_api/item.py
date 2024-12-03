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
    # Initialize variables
    pos_defaults = frappe.get_single("POS Default") if not user else None
    default_warehouse = None
    default_price_list = None

    # Determine the default warehouse
    if user:
        pos_profile = frappe.db.get_value("POS Profile User", {"default": 1, "user": user}, "parent")
        if pos_profile:
            default_warehouse = frappe.db.get_value("POS Profile", pos_profile, "warehouse")
    else:
        if pos_defaults:
            default_warehouse = pos_defaults.default_warehouse
            default_price_list = pos_defaults.default_price_list

    # Fallback if no warehouse is found
    if not default_warehouse:
        frappe.throw("Default warehouse not found. Please set it in POS Defaults or POS Profile.")

    # Fetch User Permission for Item Groups
    current_user = frappe.session.user
    allowed_groups = frappe.get_all(
        'User Permission',
        filters={'user': current_user, 'allow': 'Item Group'},
        fields=['for_value']
    )
    allowed_group_names = [group['for_value'] for group in allowed_groups]

    # Fetch all item groups with Parent Item Group in allowed_group_names
    item_groups_to_filter = []
    if allowed_group_names:
        item_groups_to_filter = frappe.get_all(
            'Item Group',
            filters={'parent_item_group': ['in', allowed_group_names]},
            fields=['name']
        )
        item_groups_to_filter = [group['name'] for group in item_groups_to_filter]

    # Add parent groups to the filter list
    item_groups_to_filter.extend(allowed_group_names)

    # Prepare filters for fetching items
    filters = [
        ['disabled', '=', 'No'],
        ['is_sales_item', '=', 1],
        ['is_stock_item', '=', 1]
    ]

    if search:
        filters.append(['item_name', 'like', f'%{search}%'])

    if item_groups_to_filter:
        filters.append(['item_group', 'in', item_groups_to_filter])

    # Fetch items based on filters
    item_details = frappe.get_all(
        'Item',
        filters=filters,
        fields=['item_code', 'item_name', 'description', 'item_group', 'stock_uom'],
        start=offset,
        page_length=limit
    )

    # Enrich item details with stock and price information
    for item in item_details:
        item['stock'] = get_stock_balance(item['item_code'], default_warehouse)
        item['price'] = frappe.get_value(
            "Item Price",
            {'item_code': item['item_code'], 'selling': 1},
            "price_list_rate"
        ) or 0.00

        # Fetch stock in other warehouses if the user has permission
        if frappe.has_permission("Bin", ptype="read", throw=False):
            warehouse_stock = frappe.get_all(
                "Bin",
                filters=[["item_code", "=", item['item_code']], ["warehouse", "!=", default_warehouse]],
                fields=["warehouse", "actual_qty"]
            )
            if warehouse_stock:
                item['other_warehouse_stock'] = [
                    {"warehouse_name": stock['warehouse'], "stock": stock['actual_qty']}
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