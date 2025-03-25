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

