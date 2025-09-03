import frappe

@frappe.whitelist()
def get_trip_form_data():
    """
    Fetch data needed to create a Delivery Trip:
    - Active drivers
    - Active vehicles
    - Active employees whose linked Department (Account) has at least one approver set
      and one of the approvers is 'martin@gmail.com'
    - Customers with at least one address (via Address -> Dynamic Link)
    - Pending delivery notes (not fully delivered)
    """

    # Drivers - Only Active
    drivers = frappe.get_all(
        "Driver",
        filters={"status": "Active"},
        fields=["name", "full_name"]
    )

    # Vehicles
    vehicles = frappe.get_all(
        "Vehicle",
        fields=["name", "license_plate"]
    )

    # Employees - Only Active and whose department has 'martin@gmail.com' as approver
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "department"]
    )

    filtered_employees = []

    for emp in employees:
        include_emp = False
        if emp.department:
            # Query the child table for the specific approver
            approvers = frappe.get_all(
                "Department Approver",
                filters={
                    "parent": emp.department,
                    "approver": "martin@gmail.com"
                },
                fields=["name", "approver"]
            )
            if approvers:
                include_emp = True

        if include_emp:
            filtered_employees.append({
                "name": emp.name,
                "employee_name": emp.employee_name,
                "department": emp.department
            })

    # Customers with at least one address (via Address -> Dynamic Link)
    all_customers = frappe.get_all(
        "Customer",
        fields=["name", "customer_name"]
    )

    customers = []
    for cust in all_customers:
        addresses = frappe.get_all(
            "Address",
            fields=["name"]
        )

        linked_addresses = []
        for addr in addresses:
            dynamic_links = frappe.get_all(
                "Dynamic Link",
                filters={
                    "parenttype": "Address",
                    "parent": addr.name,
                    "link_doctype": "Customer",
                    "link_name": cust.name
                },
                fields=["name"]
            )
            if dynamic_links:
                linked_addresses.append(addr)

        if linked_addresses:
            customers.append({
                "name": cust.name,
                "customer_name": cust.customer_name,
                "addresses": linked_addresses
            })

    # Pending Delivery Notes
    delivery_notes = frappe.get_all(
        "Delivery Note",
        filters={"status": ["in", ["To Deliver", "Partially Delivered", "To Bill"]]},
        fields=["name", "customer", "posting_date"]
    )

    return {
        "drivers": drivers,
        "vehicles": vehicles,
        "employees": filtered_employees,
        "customers": customers,
        "delivery_notes": delivery_notes
    }
