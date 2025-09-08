import frappe
from frappe import _

@frappe.whitelist()
def create_item_with_price(item_code, item_price, stock_uom="Piece", price_list="Standard Selling"):
    """Creates an Item and then creates an Item Price for it."""
    
    if frappe.db.exists("Item", item_code):
        return {"status": "error", "message": _("Item already exists")}

    try:
        # Step 1: Create and insert the Item
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_code,
            "item_group": "Mobile App",
            "stock_uom": stock_uom,
            "is_stock_item": 1
        })
        item.insert(ignore_permissions=True)

        # Step 2: Create the Item Price record
        item_price_doc = frappe.get_doc({
            "doctype": "Item Price",
            "item_code": item_code,
            "price_list": price_list,
            "price_list_rate": float(item_price),
            "selling": 1
        })
        item_price_doc.insert(ignore_permissions=True)
        
        # Step 2: Update the custom_item_price field directly in the DB
        frappe.db.set_value("Item", item_code, "custom_item_price", item_price)
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Item and price created"),
            "item_name": item.name
        }

    except Exception as e:
        frappe.log_error(message=str(e), title="Item and Price Creation Failed")
        return {"status": "error", "message": str(e)}

import frappe
from frappe import _
import json

@frappe.whitelist()
def create_item_with_prices(item_code, item_price, item_group, uoms_json=None, barcodes_json=None, stock_uom="Piece", price_list="Standard Selling"):
    """
    Creates an Item with user-defined UOMs and Barcodes, and creates an Item Price for it.

    Arguments:
    - item_code: str
    - item_price: float
    - item_group: str
    - uoms_json: JSON string (optional), e.g., '[{"uom": "Nos", "conversion_factor": 1}, {"uom": "Box", "conversion_factor": 10}]'
    - barcodes_json: JSON string (optional), e.g., '[{"barcode": "123456789012", "barcode_type": "EAN-13"}]'
    - stock_uom: str (default: "Nos")
    - price_list: str (default: "Standard Selling")
    """

    if frappe.db.exists("Item", item_code):
        return {"status": "error", "message": _("Item already exists")}

    try:
        uoms = json.loads(uoms_json) if uoms_json else []
        barcodes = json.loads(barcodes_json) if barcodes_json else []

        # Step 1: Create and insert the Item
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_code,
            "item_group": item_group,
            "stock_uom": stock_uom,
            # "custom_on_selling_pos": 1,
            "is_stock_item": 1,
            "uoms": uoms,
            "barcodes": barcodes
        })
        item.insert(ignore_permissions=True)

        # Step 2: Create the Item Price record
        item_price_doc = frappe.get_doc({
            "doctype": "Item Price",
            "item_code": item_code,
            "price_list": price_list,
            "price_list_rate": float(item_price),
            "selling": 1
        })
        item_price_doc.insert(ignore_permissions=True)

        # Step 3: Update custom field if needed
        frappe.db.set_value("Item", item_code, "custom_item_price", item_price)
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Item, UOMs, barcodes, and price created"),
            "item_name": item.name
        }

    except Exception as e:
        frappe.log_error(message=str(e), title="Item Creation Error")
        return {"status": "error", "message": str(e)}
