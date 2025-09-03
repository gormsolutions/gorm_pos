import frappe
from frappe import _

@frappe.whitelist()
def get_draft_vehicle_expenses():
    """
    Fetch all Draft Expense Claims with only 'Vehicle Expenses' child rows.
    Returns parent info and relevant child rows.
    """
    expense_claims = frappe.get_all(
        "Expense Claim",
        filters={"docstatus": 0},  # Draft only
        fields=["name", "employee", "employee_name", "expense_approver", "approval_status", "company", "posting_date"]
    )

    results = []

    for claim in expense_claims:
        doc = frappe.get_doc("Expense Claim", claim.name)
        vehicle_expenses = []

        for row in doc.expenses:
            if row.expense_type == "Vehicle Expenses":
                vehicle_expenses.append({
                    "description": row.description,
                    "amount": row.amount,
                    "sanctioned_amount": row.sanctioned_amount,
                    "expense_type": row.expense_type,
                    "idx": row.idx
                })

        # Only include parent if there are vehicle expenses
        if vehicle_expenses:
            results.append({
                "name": doc.name,
                "employee": doc.employee,
                "employee_name": doc.employee_name,
                "expense_approver": doc.expense_approver,
                "approval_status": doc.approval_status,
                "company": doc.company,
                "posting_date": doc.posting_date,
                "expenses": vehicle_expenses
            })

    return results

