import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def create_material_request(material_request_type="Material Transfer", items=None):
    """
    Create a Material Request in ERPNext.

    Args:
        material_request_type (str): Type of Material Request (default: "Material Transfer").
        items (list of dict): List of items with item_code, qty, and schedule_date.

    Example of `items`:
    [
        {
            "item_code": "ITEM001",
            "qty": 10,
            "schedule_date": "2024-12-20"
        }
    ]

    Returns:
        dict: Details of the created Material Request or error.
    """
    try:
        # Validate inputs
        if not items or not isinstance(items, list):
            frappe.throw("Items must be a list of dictionaries.")

        current_user = frappe.session.user    

        # Fetch default warehouse from User Permissions
        default_warehouse = frappe.db.get_value(
            "User Permission",
            {"user": current_user, "allow": "Warehouse"},
            "for_value"
        )

        # Fetch default cost center from User Permissions
        default_cost_center = frappe.db.get_value(
            "User Permission",
            {"user": current_user, "allow": "Cost Center"},
            "for_value"
        )

        if not default_warehouse:
            frappe.throw("Default warehouse not found. Please set it in User Permissions.")

        if not default_cost_center:
            frappe.throw("Default cost center not found. Please set it in User Permissions.")

        # Prepare Material Request items
        material_request_items = []
        for item in items:
            item_code = item.get("item_code")
            if not item_code:
                frappe.throw("Each item must have an 'item_code'.")

            # Fetch UOM from the Item doctype
            uom = frappe.db.get_value("Item", item_code, "stock_uom")
            if not uom:
                frappe.throw(f"UOM not found for Item {item_code}. Please ensure the item exists and has a valid UOM.")

            # Append item to material request list
            material_request_items.append({
                "item_code": item_code,
                "qty": item.get("qty"),
                "schedule_date": item.get("schedule_date"),
                "uom": uom,
                "warehouse": default_warehouse,
                "cost_center": default_cost_center
            })

        # Create Material Request document
        material_request = frappe.get_doc({
            "doctype": "Material Request",
            "material_request_type": material_request_type,
            "transaction_date": nowdate(),
            "items": material_request_items
        })

        # Insert and submit the document
        material_request.insert()
        material_request.submit()

        return {
            "message": "Material Request created successfully",
            "material_request": material_request.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Material Request Creation Error")
        return {
            "message": "Failed to create Material Request",
            "error": str(e)
        }


import frappe

@frappe.whitelist()
def fetch_material_requests(user=None):
    """
    Fetch all Material Requests along with their item details.
    If 'user' is provided, fetch requests created by that user.
    If not, fetch all Material Requests.
    """
    try:
        # Set filters based on the user parameter
        filters = {}
        if user:
            filters['owner'] = user

        # Fetch Material Requests based on the filters
        material_requests = frappe.get_all(
            'Material Request',
            filters=filters,
            fields=['name', 'material_request_type', 'status', 'transaction_date', 'schedule_date']
        )

        # Add item details for each Material Request
        for request in material_requests:
            items = frappe.get_all(
                'Material Request Item',
                filters={'parent': request['name']},
                fields=['item_code', 'item_name', 'qty', 'schedule_date']
            )
            request['items'] = items  # Attach items to the Material Request

        return material_requests

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Error Fetching Material Requests with Items")
        return {"error": str(e)}
