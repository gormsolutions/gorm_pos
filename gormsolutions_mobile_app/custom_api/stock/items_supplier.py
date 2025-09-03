# import frappe

# @frappe.whitelist()
# def fetch_items_and_suppliers():
#     """
#     Fetch all items with their UOM conversion details and valuation rates, and fetch all suppliers separately.
#     :return: A dictionary containing items and suppliers as separate groups.
#     """
#     try:
#         # Fetch all items
#         items_raw = frappe.db.sql("""
#             SELECT 
#                 item.name AS item_code,
#                 item.item_name,
#                 item.description,
#                 item.valuation_rate
#             FROM 
#                 `tabItem` item
#             WHERE 
#                 item.disabled = 0
#         """, as_dict=True)

#         # Group items with their details
#         items = {}
#         for item in items_raw:
#             # Fetch UOM conversion details for the item
#             uom_conversion_details = frappe.get_all(
#                 "UOM Conversion Detail",
#                 filters={"parent": item["item_code"]},
#                 fields=["uom", "conversion_factor"]
#             )

#             # Add item details to the dictionary
#             items[item["item_code"]] = {
#                 "item_name": item["item_name"],
#                  "valuation_rate": item["valuation_rate"],
#                 "uom_conversion_details": uom_conversion_details
#             }

#         # Fetch all suppliers
#         suppliers_raw = frappe.db.sql("""
#             SELECT 
#                 supplier.supplier_name
#             FROM 
#                 `tabSupplier` supplier
#             WHERE 
#                 supplier.disabled = 0
#         """, as_dict=True)

#         # Extract supplier names into a list
#         suppliers = [supplier["supplier_name"] for supplier in suppliers_raw]

#         return {
#             "status": "success",
#             "items": items,
#             "suppliers": suppliers
#         }

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Error fetching items and suppliers")
#         return {
#             "status": "error",
#             "message": f"An error occurred: {str(e)}"
#         }

import frappe

@frappe.whitelist()
def fetch_items_and_suppliers():
    """
    Fetch all items with their UOM conversion details.
    Get the most recent buying price from Item Price.
    If buying price does not exist, fallback to valuation rate from Item.
    Also fetch all active suppliers.
    """
    try:
        # Fetch all active items
        items_raw = frappe.db.sql("""
            SELECT 
                item.name AS item_code,
                item.item_name,
                item.description,
                item.valuation_rate
            FROM 
                `tabItem` item
            WHERE 
                item.disabled = 0
        """, as_dict=True)

        items = {}
        for item in items_raw:
            # Fetch UOM conversion details
            uom_conversion_details = frappe.get_all(
                "UOM Conversion Detail",
                filters={"parent": item["item_code"]},
                fields=["uom", "conversion_factor"]
            )

            # Fetch most recent buying price from Item Price
            buying_price_data = frappe.db.sql("""
                SELECT price_list_rate
                FROM `tabItem Price`
                WHERE item_code = %s AND buying = 1
                ORDER BY modified DESC
                LIMIT 1
            """, (item["item_code"],), as_dict=True)

            # Use buying price if available, otherwise fallback to valuation_rate
            buying_price = buying_price_data[0]["price_list_rate"] if buying_price_data else item["valuation_rate"] or 0.0

            items[item["item_code"]] = {
                "item_name": item["item_name"],
                "valuation_rate": buying_price,
                "uom_conversion_details": uom_conversion_details
            }

        # Fetch all active suppliers
        suppliers_raw = frappe.db.sql("""
            SELECT 
                supplier.supplier_name
            FROM 
                `tabSupplier` supplier
            WHERE 
                supplier.disabled = 0
        """, as_dict=True)

        suppliers = [supplier["supplier_name"] for supplier in suppliers_raw]

        return {
            "status": "success",
            "items": items,
            "suppliers": suppliers
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error fetching items and suppliers")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }
