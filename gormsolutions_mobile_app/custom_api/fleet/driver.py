# import frappe
# import json

# @frappe.whitelist()
# def create_driver(data):
#     """
#     Dynamic Driver creator
#     Accepts ONLY `data` as dict or JSON string
#     """

#     # Parse JSON if needed
#     if isinstance(data, str):
#         data = json.loads(data)

#     try:
#         # Ensure doctype is Driver
#         data["doctype"] = "Driver"

#         # Create document dynamically
#         doc = frappe.get_doc(data)

#         # Insert document
#         doc.insert(ignore_permissions=True)
#         frappe.db.commit()

#         return {
#             "status": "success",
#             "name": doc.name
#         }

#     except Exception as e:
#         frappe.log_error(
#             frappe.get_traceback(),
#             "Dynamic Driver Creation Failed"
#         )
#         return {
#             "status": "error",
#             "message": str(e)
#         }

import frappe
import json

@frappe.whitelist()
def create_driver(data):
    """
    Creates Employee first (if needed)
    Then creates Driver linked to Employee
    Accepts ONLY `data`
    """

    if isinstance(data, str):
        data = json.loads(data)

    try:
        data["doctype"] = "Driver"

        # -----------------------------
        # 1️⃣ CREATE EMPLOYEE FIRST
        # -----------------------------
        employee_name = data.get("employee")

        if not employee_name:
            employee_doc = frappe.get_doc({
                "doctype": "Employee",
                "first_name": data.get("full_name"),
                "employee_name": data.get("full_name"),
                "status": "Active",
                "gender": "Male",
                "date_of_birth": data.get("date_of_birth") or "1995-05-10",
                "cell_number": data.get("cell_number"),
                "date_of_joining": frappe.utils.nowdate(),
                "company": frappe.defaults.get_user_default("Company")
            })

            employee_doc.insert(ignore_permissions=True)
            employee_name = employee_doc.name

        # Attach employee to driver
        data["employee"] = employee_name

        # -----------------------------
        # 2️⃣ CREATE DRIVER
        # -----------------------------
        driver_doc = frappe.get_doc(data)
        driver_doc.insert(ignore_permissions=True)

        frappe.db.commit()

        return {
            "status": "success",
            "employee": employee_name,
            "driver": driver_doc.name
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Driver & Employee Creation Failed"
        )

        return {
            "status": "error",
            "message": frappe.get_traceback()
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
