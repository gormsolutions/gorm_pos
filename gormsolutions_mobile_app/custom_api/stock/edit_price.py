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
    

@frappe.whitelist()
def fetch_all_uoms():
    """
    Fetch all UOMs and Item Groups.
    :return: A dictionary containing lists of UOMs and Item Groups.
    """
    try:
        # Fetch UOMs
        uoms = frappe.get_all(
            "UOM",
            fields=["name", "must_be_whole_number", "enabled"]
        )

        # Fetch Item Groups
        item_groups = frappe.get_all(
            "Item Group",
            filters={"is_group": 0},  # only leaf groups if needed
            fields=["name"]
        )

        return {
            "status": "success",
            "uoms": uoms,
            "item_groups": item_groups
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error fetching UOMs and Item Groups")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }

import frappe
import json

@frappe.whitelist()
def update_selling_prices(item_code, uom, new_price, item_group=None, uoms_json=None, barcodes_json=None):
    """
    Update the selling price in the Item Price document for a given item code and UOM,
    and optionally update the item group, UOMs, and barcodes.

    :param item_code: The item code for which the price needs to be updated.
    :param uom: The unit of measure for the item price.
    :param new_price: The new selling price to be updated.
    :param item_group: (optional) New item group to update.
    :param uoms_json: (optional) JSON string of new UOMs.
    :param barcodes_json: (optional) JSON string of new barcodes.
    """
    try:
        # Step 1: Update Item Price
        item_price = frappe.get_all(
            "Item Price",
            filters={
                "item_code": item_code,
                "uom": uom,
                "price_list": "Standard Selling"
            },
            fields=["name"]
        )
        if item_price:
            item_price_doc = frappe.get_doc("Item Price", item_price[0]["name"])
        else:
            item_price_doc = frappe.new_doc("Item Price")
            item_price_doc.item_code = item_code
            item_price_doc.uom = uom
            item_price_doc.price_list = "Standard Selling"

        item_price_doc.price_list_rate = new_price
        item_price_doc.save()
        frappe.db.commit()

        # Step 2: Update Item fields
        item_doc = frappe.get_doc("Item", item_code)

        if item_group:
            item_doc.item_group = item_group

        # Update or append UOMs
        if uoms_json:
            input_uoms = json.loads(uoms_json)
            existing_uoms = {u.uom: u for u in item_doc.uoms}

            for u in input_uoms:
                if u["uom"] in existing_uoms:
                    existing_uoms[u["uom"]].conversion_factor = u["conversion_factor"]
                else:
                    item_doc.append("uoms", u)

        # Update barcode only, no append
        if barcodes_json:
            input_barcodes = json.loads(barcodes_json)
            if input_barcodes:
                new_barcode = input_barcodes[0].get("barcode")
                if item_doc.barcodes:
                    item_doc.barcodes[0].barcode = new_barcode
                else:
                    item_doc.append("barcodes", {"barcode": new_barcode})

        item_doc.save()
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Updated selling price and item data for '{item_code}'."
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error updating item and price")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }


import frappe
from frappe import _

@frappe.whitelist()
def get_item_uom_and_batch_details(item_code):
    if not item_code:
        frappe.throw(_("Item Code is required"))

    item = frappe.get_doc("Item", item_code)
    uom_details = []

    # Track UOMs already added (to avoid duplication)
    processed_uoms = set()

    # === Add stock UOM first ===
    stock_uom_price = frappe.get_value(
        "Item Price",
        {"item_code": item.item_code, "selling": 1, "uom": item.stock_uom},
        "price_list_rate"
    ) or 0.00

    uom_details.append({
        "uom": item.stock_uom,
        "conversion_factor": 1,
        "price": stock_uom_price
    })
    processed_uoms.add(item.stock_uom)

    # === Fetch additional UOMs and their prices ===
    conversion_details = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": item.item_code},
        fields=["uom", "conversion_factor"]
    )

    for conv in conversion_details:
        uom = conv["uom"]
        if uom not in processed_uoms:
            price = frappe.get_value(
                "Item Price",
                {"item_code": item.item_code, "selling": 1, "uom": uom},
                "price_list_rate"
            ) or 0.00
            uom_details.append({
                "uom": uom,
                "conversion_factor": conv.get("conversion_factor", 1),
                "price": price
            })
            processed_uoms.add(uom)

    # === Get only one barcode for the item (if available) ===
    barcode = frappe.get_value(
        "Item Barcode",
        {"parent": item.item_code},
        "barcode"
    ) or ""

    return {
        "item_code": item.item_code,
        "item_name": item.item_name,
        "stock_uom": item.stock_uom,
        "stock_uom_price": stock_uom_price,
        "uom_details": uom_details,
        "barcode": barcode
    }
