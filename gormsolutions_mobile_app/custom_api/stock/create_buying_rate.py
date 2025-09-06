import frappe

def create_item_price_from_purchase_invoice(doc, method):
    """
    On Purchase Invoice submit:
    - Update existing Buying Item Price if rate is different
    - Create a new Item Price only if none exists
    """

    buying_price_list = "Standard Buying"

    for item in doc.items:
        if not item.item_code:
            continue

        # Build filter for existing Item Prices
        filters = {
            "item_code": item.item_code,
            "price_list": buying_price_list,
            "uom": item.uom,
            "buying": 1,
            "currency": doc.currency
        }

        if doc.supplier:
            filters["supplier"] = doc.supplier

        # Fetch existing Item Prices
        existing_prices = frappe.get_all(
            "Item Price",
            filters=filters,
            fields=["name", "price_list_rate"]
        )

        if existing_prices:
            # Update first matching price if rate is different
            ip_name = existing_prices[0]["name"]
            existing_rate = float(existing_prices[0]["price_list_rate"])
            if existing_rate != float(item.rate):
                ip = frappe.get_doc("Item Price", ip_name)
                ip.price_list_rate = item.rate
                ip.valid_from = doc.posting_date
                ip.save(ignore_permissions=True)
        else:
            # Create new Item Price if none exists
            ip = frappe.new_doc("Item Price")
            ip.item_code = item.item_code
            ip.price_list = buying_price_list
            ip.uom = item.uom
            ip.price_list_rate = item.rate
            ip.currency = doc.currency
            ip.buying = 1
            ip.supplier = doc.supplier if doc.supplier else None
            ip.valid_from = doc.posting_date
            ip.save(ignore_permissions=True)

    frappe.db.commit()
