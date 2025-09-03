import frappe

@frappe.whitelist()
def get_supplier_items():
    """
    Fetch all items with:
    - UOMs and their purchase rates
    - Suppliers
    """
    # Fetch all purchase items
    items = frappe.get_all(
        "Item",
        filters={"disabled": 0, "is_purchase_item": 1},
        fields=["item_code", "item_name", "description", "item_group", "image", "stock_uom"]
    )

    # Prepare item_codes list to fetch related data in bulk
    item_codes = [item["item_code"] for item in items]

    # Fetch all UOM conversions in bulk
    uom_conversions = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": ["in", item_codes]},
        fields=["parent", "uom", "conversion_factor"]
    )

    # Fetch all item prices in bulk
    item_prices = frappe.get_all(
        "Item Price",
        filters={"item_code": ["in", item_codes], "buying": 1},
        fields=["item_code", "uom", "price_list_rate"]
    )
    price_map = {}
    for price in item_prices:
        price_map.setdefault(price["item_code"], {})[price["uom"]] = price["price_list_rate"]

    # Fetch all suppliers in bulk
    suppliers = frappe.get_all(
        "Item Supplier",
        filters={"parent": ["in", item_codes]},
        fields=["parent", "supplier"]
    )
    supplier_map = {}
    for sup in suppliers:
        supplier_map.setdefault(sup["parent"], []).append({
            "supplier": sup["supplier"],
         })

    # Group UOM conversions by item
    uom_map = {}
    for conv in uom_conversions:
        uom_map.setdefault(conv["parent"], []).append(conv)

    # Build final item payload
    for item in items:
        uom_details = []

        # Add stock UOM
        stock_uom = item["stock_uom"]
        uom_details.append({
            "uom": stock_uom,
            "conversion_factor": 1,
            "price": price_map.get(item["item_code"], {}).get(stock_uom, 0.0)
        })

        # Add conversion UOMs (skip duplicates of stock UOM)
        for conv in uom_map.get(item["item_code"], []):
            if conv["uom"] != stock_uom:
                uom_details.append({
                    "uom": conv["uom"],
                    "conversion_factor": conv.get("conversion_factor", 1),
                    "price": price_map.get(item["item_code"], {}).get(conv["uom"], 0.0)
                })

        item["uom_details"] = uom_details
        item["suppliers"] = supplier_map.get(item["item_code"], [])

    return items
