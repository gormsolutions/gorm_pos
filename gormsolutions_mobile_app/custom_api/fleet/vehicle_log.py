import frappe

@frappe.whitelist()
def fetch_all_vehicle_logs():
    """
    Fetch all Vehicle Log documents with all fields, child tables,
    plus the human-readable names of the linked Driver and Employee.
    :return: list[dict]
    """
    # Grab every Vehicle Log, newest first
    log_names = frappe.get_all(
        "Vehicle Log",
        fields=["name"],
        order_by="creation desc",
        pluck="name"
    )

    out = []
    for name in log_names:
        doc = frappe.get_doc("Vehicle Log", name)

        # Resolve human-readable names (1 query each, only when needed)
        driver_name = (
            frappe.db.get_value("Driver", doc.custom_driver_name, "full_name")
            if doc.get("custom_driver_name")
            else None
        )

        employee_name = (
            frappe.db.get_value("Employee", doc.employee, "employee_name")
            if doc.get("employee")
            else None
        )

        # Convert the doc to dict so we can inject the extra keys
        row = doc.as_dict()
        row["driver_name"] = driver_name
        row["employee_name"] = employee_name
        out.append(row)

    return out

