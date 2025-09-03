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
