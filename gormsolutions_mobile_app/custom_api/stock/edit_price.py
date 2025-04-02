import frappe

@frappe.whitelist()
def update_selling_price(item_code, uom, new_price):
    """
    Update the selling price in the Item Price document for a given item code and UOM.
    :param item_code: The item code for which the price needs to be updated.
    :param uom: The unit of measure for the item.
    :param new_price: The new selling price to be updated.
    """
    try:
        # Fetch the Item Price document for the given item code and UOM
        item_price = frappe.get_all(
            "Item Price",
            filters={
                "item_code": item_code,
                "uom": uom,
                "price_list": "Standard Selling"  # Assuming the price list is 'Standard Selling'
            },
            fields=["name"]
        )

        if not item_price:
            return {
                "status": "error",
                "message": f"No Item Price found for item code '{item_code}' and UOM '{uom}'."
            }

        # Get the first matching Item Price document
        item_price_doc = frappe.get_doc("Item Price", item_price[0]["name"])

        # Update the price_list_rate with the new price
        item_price_doc.price_list_rate = new_price
        item_price_doc.save()

        # Commit the transaction
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Selling price for item '{item_code}' with UOM '{uom}' updated to {new_price}."
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error updating selling price")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }