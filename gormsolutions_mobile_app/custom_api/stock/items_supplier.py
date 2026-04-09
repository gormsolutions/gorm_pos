import frappe

@frappe.whitelist()
def fetch_items_and_suppliers():
    """
    Fetch all items with their UOM conversion details and valuation rates, and fetch all suppliers separately.
    :return: A dictionary containing items and suppliers as separate groups.
    """
    try:
        # Fetch all items
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

        # Group items with their details
        items = {}
        for item in items_raw:
            # Fetch UOM conversion details for the item
            uom_conversion_details = frappe.get_all(
                "UOM Conversion Detail",
                filters={"parent": item["item_code"]},
                fields=["uom", "conversion_factor"]
            )

            # Add item details to the dictionary
            items[item["item_code"]] = {
                "item_name": item["item_name"],
                 "valuation_rate": item["valuation_rate"],
                "uom_conversion_details": uom_conversion_details
            }

        # Fetch all suppliers
        suppliers_raw = frappe.db.sql("""
            SELECT 
                supplier.supplier_name
            FROM 
                `tabSupplier` supplier
            WHERE 
                supplier.disabled = 0
        """, as_dict=True)

        # Extract supplier names into a list
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