import frappe
from frappe import _

@frappe.whitelist()
def get_expenses_with_trip_and_log():
    """
    Fetch all Draft Expense Claims where at least one of vehicle_log or delivery_trip is set (not empty or None).
    Returns parent fields and child table details.
    """
    # Fetch all draft Expense Claims
    draft_claims = frappe.get_all(
        "Expense Claim",
        filters={
            "docstatus": 0,
            "approval_status": "Draft"  
                 },
        fields=["name", "employee", "expense_approver", "approval_status", "department", "vehicle_log", "delivery_trip"]
    )

    results = []

    for claim in draft_claims:
        # Include claims where at least one field is set
        if claim.vehicle_log or claim.delivery_trip:
            # Fetch child table 'expenses'
            expenses = frappe.get_all(
                "Expense Claim Detail",
                filters={"parent": claim.name, "parenttype": "Expense Claim"},
                fields=["description", "amount", "sanctioned_amount", "expense_type"]
            )

            results.append({
                "expense_claim": claim.name,
                "employee": claim.employee,
                "expense_approver": claim.expense_approver,
                "approval_status": claim.approval_status,
                "department": claim.department,
                "vehicle_log": claim.vehicle_log,
                "delivery_trip": claim.delivery_trip,
                "expenses": expenses
            })

    return results
