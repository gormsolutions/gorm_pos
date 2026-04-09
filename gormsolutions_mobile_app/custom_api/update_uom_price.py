import frappe

@frappe.whitelist()
def update_all_item_prices_uom():
    items = frappe.get_all("Item", fields=["item_code", "stock_uom"])
    
    if not items:
        return "No Items found."

    updated_count = 0
    for item in items:
        item_prices = frappe.get_all("Item Price", 
                                     filters={"item_code": item["item_code"], "selling": 1}, 
                                     fields=["name", "uom"])
        
        for item_price in item_prices:
            # Check if the current UOM is different from the stock_uom
            if item_price["uom"] != item["stock_uom"]:
                frappe.db.set_value("Item Price", item_price["name"], "uom", item["stock_uom"])
                updated_count += 1

    frappe.db.commit()
    return f"Updated {updated_count} Item Price records where UOM was different."

import frappe
from frappe import _

@frappe.whitelist()
def update_uoms_for_all_item_prices(item_code):
    item = frappe.get_doc("Item", item_code)

    if not item.uoms:
        frappe.throw(_("No UOMs found on the item."))

    # Sort UOMs descending by conversion factor
    sorted_uoms = sorted(item.uoms, key=lambda x: x.conversion_factor or 0, reverse=True)

    # Get all Standard Selling Item Prices for this item sorted descending by price_list_rate
    item_prices = frappe.db.sql("""
        SELECT name, uom, price_list_rate
        FROM `tabItem Price`
        WHERE item_code = %s AND price_list = 'Standard Selling'
        ORDER BY price_list_rate DESC
    """, (item_code,), as_dict=True)

    if not item_prices:
        return "❌ No 'Standard Selling' Item Price found."

    # Pair them one-to-one based on the sorted order (up to min length)
    limit = min(len(sorted_uoms), len(item_prices))

    updated = []
    for i in range(limit):
        uom_to_set = sorted_uoms[i].uom
        price = frappe.get_doc("Item Price", item_prices[i].name)

        if price.uom != uom_to_set:
            price.uom = uom_to_set
            price.save()
            updated.append(f"{price.name} → {uom_to_set}")

    if updated:
        return f"✅ Updated UOMs:\n" + "\n".join(updated)
    else:
        return "✅ All UOMs already correct."

import frappe
from frappe import _

@frappe.whitelist()
def update_all_item_prices_uoms():
    items = frappe.get_all("Item", fields=["name"])
    updated = []

    for item in items:
        doc = frappe.get_doc("Item", item.name)

        if not doc.uoms:
            continue  # Skip items without UOMs

        # Sort UOMs descending by conversion factor
        sorted_uoms = sorted(doc.uoms, key=lambda x: x.conversion_factor or 0, reverse=True)

        # Fetch all Standard Selling Item Prices ordered by price_list_rate desc
        item_prices = frappe.db.sql("""
            SELECT name, uom, price_list_rate
            FROM `tabItem Price`
            WHERE item_code = %s AND price_list = 'Standard Selling'
            ORDER BY price_list_rate DESC
        """, (item.name,), as_dict=True)

        if not item_prices:
            continue

        # For each item price, update the UOM corresponding by index
        # If more item prices than UOMs, repeat last UOM for remaining
        for i, price_data in enumerate(item_prices):
            uom_to_set = sorted_uoms[i].uom if i < len(sorted_uoms) else sorted_uoms[-1].uom
            price_doc = frappe.get_doc("Item Price", price_data['name'])

            if price_doc.uom != uom_to_set:
                price_doc.uom = uom_to_set
                price_doc.save()
                updated.append(f"{price_doc.name} ({item.name}) updated to UOM: {uom_to_set}")

    if updated:
        return f"✅ Updated {len(updated)} Item Price records:\n" + "\n".join(updated)
    else:
        return "✅ No updates needed, all UOMs already correct."
