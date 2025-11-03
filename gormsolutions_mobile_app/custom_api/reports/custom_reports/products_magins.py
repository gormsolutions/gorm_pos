import frappe

@frappe.whitelist()
def get_products_with_margins(search=None, start=0, page_length=20, download=0):
    """
    Fetch item list with cost, selling price, and margin.
    If download=1, returns all items ignoring pagination.
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
            ["item_code", "like", f"%{search}%"],
            ["item_name", "like", f"%{search}%"]
        ]

    items = frappe.get_list(
        "Item",
        fields=["item_code", "item_name", "valuation_rate"],
        filters=filters,
        or_filters=or_filters,
        limit_start=start,
        limit_page_length=page_length,
        order_by="modified desc",
        ignore_permissions=True,
    )

    result = []
    for item in items:
        item_code = item.item_code

        # Cost lookup: Purchase -> Stock Ledger -> Sales -> Valuation Rate
        cost = (
            frappe.db.get_value("Purchase Invoice Item", {"item_code": item_code}, "base_rate", order_by="creation desc")
            or frappe.db.get_value("Stock Ledger Entry", {"item_code": item_code}, "valuation_rate", order_by="posting_date desc")
            or frappe.db.get_value("Sales Invoice Item", {"item_code": item_code}, "base_rate", order_by="creation desc")
            or item.valuation_rate
            or 0
        )

        # Selling price from Item Price or Sales Invoice
        selling_price = (
            frappe.db.get_value("Item Price", {"item_code": item_code, "selling": 1}, "price_list_rate", order_by="creation desc")
            or frappe.db.get_value("Sales Invoice Item", {"item_code": item_code}, "base_rate", order_by="creation desc")
            or 0
        )

        result.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "cost": float(cost or 0),
            "selling_price": float(selling_price or 0),
        })

    return result
