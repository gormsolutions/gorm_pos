import frappe

@frappe.whitelist()
def get_supplier_goods_items(supplier):
    if not supplier:
        return []

    # Find Supplier Good record for the supplier
    doc = frappe.get_all("Supplier Good", filters={"supplier": supplier}, limit=1)
    if not doc:
        return []

    supplier_good = frappe.get_doc("Supplier Good", doc[0].name)
    items = []

    for row in supplier_good.items:
        item_code = row.item
   
        # Step 1: Get default purchase_uom from Item
        item_doc = frappe.get_doc("Item", item_code)
        purchase_uom = item_doc.purchase_uom or item_doc.stock_uom

        # Step 2: Get conversion factor for that UOM 
        conversion_factor = frappe.db.get_value(
            "UOM Conversion Detail",
            {
                "parent": item_code,
                "uom": purchase_uom
            },
            "conversion_factor"
        ) or 1

        items.append({
            "item_code": item_code,
            "item_name":item_doc.item_name,
            "uom": purchase_uom,
            "rate": row.rate,
            "conversion_factor": conversion_factor,
            "qty": 1
        })

    return items
