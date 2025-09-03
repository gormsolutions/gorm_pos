# my_app/api/purchase_invoice.py
import frappe

@frappe.whitelist()
def get_supplier_items(supplier):
    """
    Fetch all items linked to a supplier, including:
    - purchase_uom
    - rate
    - uom_conversion_factor
    - accepted_qty_in_stock_uom
    """
    # Get all item codes linked to this supplier
    items = frappe.get_all(
        "Item Supplier",
        filters={"supplier": supplier},
        fields=["parent as item_code"]
    )

    item_list = []
    for i in items:
        item = frappe.get_doc("Item", i.item_code)

        # Determine purchase UOM
        purchase_uom = item.purchase_uom if item.purchase_uom else item.stock_uom

        # Rate from Item Price
        rate = frappe.db.get_value(
            "Item Price",
            {"item_code": item.name, "buying": 1, "uom": purchase_uom},
            "price_list_rate"
        ) or 0

        # UOM Conversion Factor
        conversion_factor = 1
        if purchase_uom != item.stock_uom:
            conversion_factor = frappe.db.get_value(
                "UOM Conversion Detail",
                {"parent": item.name, "uom": purchase_uom},
                "conversion_factor"
            ) or 1

        # Default purchase qty
        purchase_qty = 1

        # Accepted Qty in Stock UOM
        accepted_qty_stock_uom = purchase_qty * conversion_factor

        item_list.append({
            "item_code": item.name,
            "item_name": item.item_name,
            "description": item.description,
            "uom": purchase_uom,
            "rate": rate,
            "conversion_factor": conversion_factor,
            "accepted_qty_stock_uom": accepted_qty_stock_uom
        })

    return item_list
