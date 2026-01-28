import frappe

@frappe.whitelist()
def fetch_all_employees():
    """
    Fetch all employees with important fields only
    """

    employees = frappe.get_all(
        "Employee",
        fields=[
            "name",
            "employee",
            "employee_name",
            "status",
            "department",
            "designation",
            "company",
            "cell_number",
            "date_of_joining"
        ],
        order_by="creation desc"
    )

    return {
        "status": "success",
        "count": len(employees),
        "data": employees
    }
