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
        items.append({
            "item_code": row.item,
            "uom": row.uom,
            "rate": row.rate,
            "qty": 1  # Default quantity, you can change this
        })

    return items
