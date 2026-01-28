import frappe

@frappe.whitelist()
def get_all_vehicles_with_names():
    """
    Fetch all Vehicle records along with linked Driver and Employee names.
    """
    vehicles = frappe.get_all(
        "Vehicle",
        fields=[
            "name",
            "make",
            "model",
            "custom_driver",
            "last_odometer",
            "acquisition_date",
            "location",
            "chassis_no",
            "vehicle_value",
            "employee",
            "insurance_company",
            "policy_no",
            "custom_isuing_office",
            "start_date",
            "end_date",
            "fuel_type",
            "uom",
            "carbon_check_date",
            "color",
            "wheels",
            "doors"
        ],
        order_by="creation desc"
    )

    results = []
    for v in vehicles:
        # Get driver name
        driver_name = None
        if v.custom_driver:
            driver_name = frappe.db.get_value("Driver", v.custom_driver, "full_name")

        # Get employee name
        employee_name = None
        if v.employee:
            employee_name = frappe.db.get_value("Employee", v.employee, "employee_name")

        v["driver_name"] = driver_name
        v["employee_name"] = employee_name
        results.append(v)

    return results


import frappe

@frappe.whitelist()
def create_vehicle_from_data():
    data = frappe.form_dict.get("data")

    if isinstance(data, str):
        data = frappe.parse_json(data)

    vehicle = frappe.get_doc({
        "doctype": "Vehicle",
        **data
    })

    vehicle.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "vehicle": vehicle.name
    }


import frappe

@frappe.whitelist()
def update_vehicle():
    data = frappe.form_dict.get("data")

    if not data:
        frappe.throw("No data provided")

    if isinstance(data, str):
        data = frappe.parse_json(data)

    # You can match by name OR license_plate
    vehicle_name = data.get("name")

    if not vehicle_name and data.get("license_plate"):
        vehicle_name = frappe.db.get_value(
            "Vehicle",
            {"license_plate": data.get("license_plate")},
            "name"
        )

    if not vehicle_name:
        frappe.throw("Vehicle not found")

    vehicle = frappe.get_doc("Vehicle", vehicle_name)

    # Update only provided fields
    for field, value in data.items():
        if field not in ("doctype", "name"):
            vehicle.set(field, value)

    vehicle.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "vehicle": vehicle.name
    }
