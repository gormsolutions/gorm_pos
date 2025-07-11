import frappe
from erpnext.stock.utils import get_stock_balance

@frappe.whitelist()
def get_item_details(limit, offset, search=None, user=None):
    current_user = user or frappe.session.user

    # --- Step 1: Find POS Profile assigned to user ---
    pos_profiles = frappe.get_all("POS Profile", filters={"disabled": 0}, fields=["name"])
    pos_profile_name = None
    for profile in pos_profiles:
        user_found = frappe.get_all(
            "POS Profile User",
            filters={"parent": profile.name, "user": current_user},
            limit=1
        )
        if user_found:
            pos_profile_name = profile.name
            break

    if not pos_profile_name:
        return []

    # --- Step 2: Get permitted Item Groups from POS Profile ---
    pos_profile = frappe.get_doc("POS Profile", pos_profile_name)
    permitted_item_groups = [row.item_group for row in pos_profile.item_groups if row.item_group]

    if not permitted_item_groups:
        return []

    # --- Step 2.5: Get selling price list from POS Profile ---
    selling_price_list = pos_profile.selling_price_list
    if not selling_price_list:
        return []

    # --- Step 3: Get all child item groups ---
    item_groups_to_filter = permitted_item_groups[:]
    child_groups = frappe.get_all(
        "Item Group",
        filters={"parent_item_group": ["in", permitted_item_groups]},
        fields=["name"]
    )
    item_groups_to_filter.extend([grp["name"] for grp in child_groups])

    # --- Step 4: Get default warehouse from POS Profile ---
    default_warehouse = pos_profile.warehouse
    if not default_warehouse:
        frappe.throw("Warehouse is not set in the POS Profile.")

    # --- Step 5: Build item filters ---
    filters = [
        ["disabled", "=", 0],
        ["is_sales_item", "=", 1],
        # ["is_stock_item", "=", 1],
    ]
    if search:
        filters.append(["item_name", "like", f"%{search}%"])
    if item_groups_to_filter:
        filters.append(["item_group", "in", item_groups_to_filter])
    else:
        return []

    # --- Step 6: Fetch items ---
    item_details = frappe.get_all(
        "Item",
        filters=filters,
        fields=["item_code", "item_name", "description", "item_group", "image", "stock_uom"],
        start=offset,
        page_length=limit,
    )

    # --- Step 7: Enrich items with stock, price, UOM info ---
    for item in item_details:
        item["stock"] = get_stock_balance(item["item_code"], default_warehouse) or 0

        uom_details = [{
            "uom": item["stock_uom"],
            "conversion_factor": 1,
            "price": 0.00
        }]

        conversion_details = frappe.get_all(
            "UOM Conversion Detail",
            filters={"parent": item["item_code"]},
            fields=["uom", "conversion_factor"]
        )

        # Other UOMs
        for conv in conversion_details:
            if conv["uom"] != item["stock_uom"]:
                price = frappe.get_value(
                    "Item Price",
                    {
                        "item_code": item["item_code"],
                        "selling": 1,
                        "uom": conv["uom"],
                        "price_list": selling_price_list
                    },
                    "price_list_rate"
                ) or 0.00
                uom_details.append({
                    "uom": conv["uom"],
                    "conversion_factor": conv.get("conversion_factor", 1),
                    "price": price
                })

        # Stock UOM price
        stock_uom_price = frappe.get_value(
            "Item Price",
            {
                "item_code": item["item_code"],
                "selling": 1,
                "uom": item["stock_uom"],
                "price_list": selling_price_list
            },
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
                    ["warehouse", "!=", default_warehouse],
                ],
                fields=["warehouse", "actual_qty"],
            )
            item["other_warehouse_stock"] = [
                {"warehouse_name": stock["warehouse"], "stock": stock["actual_qty"]}
                for stock in warehouse_stock
            ]

    return item_details
