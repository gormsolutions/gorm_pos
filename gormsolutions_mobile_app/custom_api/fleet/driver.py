import frappe
import json

@frappe.whitelist()
def create_driver(data):
    """
    Dynamic Driver creator
    Accepts ONLY `data` as dict or JSON string
    """

    # Parse JSON if needed
    if isinstance(data, str):
        data = json.loads(data)

    try:
        # Ensure doctype is Driver
        data["doctype"] = "Driver"

        # Create document dynamically
        doc = frappe.get_doc(data)

        # Insert document
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "name": doc.name
        }

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Dynamic Driver Creation Failed"
        )
        return {
            "status": "error",
            "message": str(e)
        }

import frappe

@frappe.whitelist()
def fetch_all_drivers():
    """
    Fetch all Drivers with important fields only
    """

    try:
        drivers = frappe.get_all(
            "Driver",
            fields=[
                "name",
                "full_name",
                "status",
                "employee",
                "cell_number",
                "license_number",
                "issuing_date",
                "expiry_date"
            ],
            order_by="creation desc"
        )

        return {
            "status": "success",
            "count": len(drivers),
            "data": drivers
        }

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Fetch All Drivers Failed"
        )
        return {
            "status": "error",
            "message": str(e)
        }
