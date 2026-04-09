import frappe

def before_save_product_bundle(doc, method):
    # Calculate total qty
    total_qty = sum([item.qty or 0 for item in doc.items])
    doc.custom_total_qty = total_qty

    # Calculate amount per BOM item and total bakery cost
    total_bakery_cost = 0
    for bom_item in doc.custom_bom_items:
        qty = bom_item.qty or 0
        cost = bom_item.bakery_cost or 0
        bom_item.amount = qty * cost
        total_bakery_cost += bom_item.amount

    doc.custom_total_bakery_cost = total_bakery_cost
