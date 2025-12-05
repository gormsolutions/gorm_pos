import frappe

@frappe.whitelist()
def get_products_with_margins(search=None, start=0, page_length=20, download=0):
    """
    Fetch Product Bundles with bakery cost, icing qty, selling price, and margin.
    """
    start = int(start or 0)
    page_length = int(page_length or 20)
    download = int(download or 0)

    if download:
        start = 0
        page_length = 100000  # arbitrary large number

    filters = [["disabled", "=", 0]]
    or_filters = None

    if search:
        or_filters = [
            ["new_item_code", "like", f"%{search}%"],
            ["description", "like", f"%{search}%"]
        ]

    items = frappe.get_list(
        "Product Bundle",
        fields=["new_item_code","description", "custom_total_bakery_cost", "custom_total_qty"],
        filters=filters,
        or_filters=or_filters,
        limit_start=start,
        limit_page_length=page_length,
        order_by="modified desc",
        ignore_permissions=True,
    )

    result = []
    for item in items:
        item_code = item.new_item_code

        selling_price = (
            frappe.db.get_value("Item Price", {"item_code": item_code, "selling": 1}, "price_list_rate", order_by="creation desc")
            or frappe.db.get_value("Sales Invoice Item", {"item_code": item_code}, "base_rate", order_by="creation desc")
            or 0
        )

        total_cost = (item.custom_total_bakery_cost or 0) + (item.custom_total_qty or 0)
        margin = float(selling_price or 0) - total_cost
        margin_pct = total_cost and (margin / total_cost * 100) or 0

        result.append({
            "item_code": item.new_item_code,
            "item_name": item.description,
            "cost": item.custom_total_bakery_cost or 0,
            "icing_cost": item.custom_total_qty or 0,
            "total_cost": total_cost,
            "selling_price": float(selling_price or 0),
            "margin": margin,
            "margin_pct": round(margin_pct, 2),
        })

    return result
