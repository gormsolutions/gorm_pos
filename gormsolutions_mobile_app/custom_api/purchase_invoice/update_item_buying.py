import frappe

@frappe.whitelist()
def update_item_buying_price(doc, method):
    updated_items = []
    
    for item in doc.items:
        # Update item price in "Standard Buying" price list
        frappe.db.set_value("Item Price", {
            "item_code": item.item_code,
            "price_list": "Standard Buying"
        }, "price_list_rate", item.rate)
        
        updated_items.append(f"{item.item_code}: {item.rate}")

    frappe.db.commit()

    # Show message in UI
    if updated_items:
        frappe.msgprint("Updated Buying Prices:<br>" + "<br>".join(updated_items),alert=True, indicator='green')

