import frappe

@frappe.whitelist(allow_guest=True)
def create_stock_entry(stock_entry_type, items, from_warehouse=None, to_warehouse=None, company=None, posting_date=None):
    """
    Create and submit a Stock Entry in ERPNext.
    
    Args:
        stock_entry_type (str): Type of stock entry (e.g., "Material Transfer").
        items (list): List of dictionaries with item details, each having:
                      - item_code (str): Item code.
                      - qty (float): Quantity.
                      - uom (str): Unit of Measure.
                      - s_warehouse (str, optional): Source warehouse.
                      - t_warehouse (str, optional): Target warehouse.
        from_warehouse (str, optional): Default source warehouse.
        to_warehouse (str, optional): Default target warehouse.
        company (str, optional): The company for the stock entry.
        posting_date (str, optional): Date of the stock entry (YYYY-MM-DD).
        
    Returns:
        dict: Success or error message.
    """
    # Validate required parameters
    if not stock_entry_type or not items:
        return {"error": "Stock entry type and items are required."}
    
    # Validate the 'items' parameter to ensure it's a list of dictionaries
    if not isinstance(items, list):
        return {"error": "Items must be a list."}
    
    for item in items:
        if not isinstance(item, dict):
            return {"error": "Each item must be a dictionary."}
        if not item.get("item_code") or not item.get("qty") or not item.get("uom"):
            return {"error": "Each item must have item_code, qty, and uom."}

    try:
        # Create Stock Entry document
        stock_entry = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": stock_entry_type,
            "company": company or frappe.defaults.get_user_default("Company"),
            "posting_date": posting_date or frappe.utils.nowdate(),
            "items": []
        })
        
        # Get cost centers permitted for the current user
        current_user = frappe.session.user
        cost_center_permitted = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Cost Center"},
            fields=["for_value"]
        )
        
        # Default cost center to use (hardcoded or fetched from permissions)
        default_cost_centers = [perm["for_value"] for perm in cost_center_permitted]
        
        if not default_cost_centers:
            return {"error": "No permitted cost centers found for the current user."}
        
        # Add items to the Stock Entry
        for item in items:
            # Ensure required item fields are present
            item_code = item.get("item_code")
            qty = item.get("qty")
            uom = item.get("uom")
            s_warehouse = item.get("s_warehouse", from_warehouse)
            t_warehouse = item.get("t_warehouse", to_warehouse)
            
            # Validate individual item data
            if not item_code or not qty or not uom:
                return {"error": "Item must have item_code, qty, and uom."}
            
            stock_entry.append("items", {
                "item_code": item_code,
                "qty": qty,
                "uom": uom,
                "cost_center": default_cost_centers[0],  # Use the first permitted cost center
                "s_warehouse": s_warehouse,
                "t_warehouse": t_warehouse,
            })
        
        # Save and Submit the Stock Entry
        stock_entry.insert(ignore_permissions=True)
        stock_entry.submit()
        
        return {
            "message": "Stock entry created and submitted successfully.",
            "name": stock_entry.name
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Stock Entry API Error")
        return {"error": str(e)}
