# import frappe

# @frappe.whitelist()
# def get_products_with_margins(search=None, start=0, page_length=20, download=0):
#     """
#     Fetch Product Bundles with bakery cost, icing qty, selling price, and margin.
#     """
#     start = int(start or 0)
#     page_length = int(page_length or 20)
#     download = int(download or 0)

#     if download:
#         start = 0
#         page_length = 100000  # arbitrary large number

#     filters = [["disabled", "=", 0]]
#     or_filters = None

#     if search:
#         or_filters = [
#             ["new_item_code", "like", f"%{search}%"],
#             ["description", "like", f"%{search}%"]
#         ]

#     items = frappe.get_list(
#         "Product Bundle",
#         fields=["new_item_code","description", "custom_total_bakery_cost", "custom_total_qty"],
#         filters=filters,
#         or_filters=or_filters,
#         limit_start=start,
#         limit_page_length=page_length,
#         order_by="modified desc",
#         ignore_permissions=True,
#     )

#     result = []
#     for item in items:
#         item_code = item.new_item_code

#         selling_price = (
#             frappe.db.get_value("Item Price", {"item_code": item_code, "selling": 1}, "price_list_rate", order_by="creation desc")
#             or frappe.db.get_value("Sales Invoice Item", {"item_code": item_code}, "base_rate", order_by="creation desc")
#             or 0
#         )

#         total_cost = (item.custom_total_bakery_cost or 0) + (item.custom_total_qty or 0)
#         margin = float(selling_price or 0) - total_cost
#         margin_pct = total_cost and (margin / total_cost * 100) or 0

#         result.append({
#             "item_code": item.new_item_code,
#             "item_name": item.description,
#             "cost": item.custom_total_bakery_cost or 0,
#             "icing_cost": item.custom_total_qty or 0,
#             "total_cost": total_cost,
#             "selling_price": float(selling_price or 0),
#             "margin": margin,
#             "margin_pct": round(margin_pct, 2),
#         })

#     return result


import frappe

@frappe.whitelist()
def get_products_with_margins(search=None, start=0, page_length=20, download=0):
    """
    Fetch Product Bundles with costs, margins,
    and Labour Overhead cost calculated from buying / valuation rate.
    """
    start = int(start or 0)
    page_length = int(page_length or 20)
    download = int(download or 0)

    if download:
        start = 0
        page_length = 100000

    filters = [["disabled", "=", 0]]
    or_filters = None

    if search:
        or_filters = [
            ["new_item_code", "like", f"%{search}%"],
            ["description", "like", f"%{search}%"]
        ]

    items = frappe.get_list(
        "Product Bundle",
        fields=[
            "name",
            "new_item_code",
            "description",
            "custom_total_bakery_cost",
            "custom_total_qty"
        ],
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

        # Selling price
        selling_price = (
            frappe.db.get_value(
                "Item Price",
                {"item_code": item_code, "selling": 1},
                "price_list_rate",
                order_by="creation desc"
            )
            or frappe.db.get_value(
                "Sales Invoice Item",
                {"item_code": item_code},
                "base_rate",
                order_by="creation desc"
            )
            or 0
        )

        # Labour Overhead row
        labour = frappe.db.get_value(
            "Product Bundle Item",
            {
                "parent": item.name,
                "item_code": "Labour Overhead"
            },
            ["item_code", "qty"],
            as_dict=True
        )

        labour_rate = 0
        labour_buying_rate = 0

        if labour:
            # Buying price first
            labour_buying_rate = (
                frappe.db.get_value(
                    "Item Price",
                    {"item_code": labour.item_code, "buying": 1},
                    "price_list_rate",
                    order_by="creation desc"
                )
                or frappe.db.get_value(
                    "Item",
                    labour.item_code,
                    "valuation_rate"
                )
                or 0
            )

            labour_rate = labour.qty * labour_buying_rate

        bakery_cost = item.custom_total_bakery_cost or 0
        icing_cost = item.custom_total_qty or 0

        total_cost = bakery_cost + icing_cost + labour_rate
        margin = float(selling_price or 0) - total_cost
        margin_pct = (margin / total_cost * 100) if total_cost else 0

        result.append({
            "item_code": item.new_item_code,
            "item_name": item.description,

            "bakery_cost": bakery_cost,
            "icing_cost": icing_cost,

            # Labour Overhead
            "labour_item_name": labour.item_name if labour else None,
            "labour_qty": labour.qty if labour else 0,
            "labour_unit_rate": labour_buying_rate,
            "labour_total_rate": labour_rate,

            "total_cost": total_cost,
            "selling_price": float(selling_price or 0),
            "margin": margin,
            "margin_pct": round(margin_pct, 2),
        })

    return result

