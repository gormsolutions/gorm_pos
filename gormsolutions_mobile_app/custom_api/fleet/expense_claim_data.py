import frappe
from frappe import _

@frappe.whitelist()
def get_expense_claims():
    """
    Fetch all Draft Expense Claims (docstatus = 0)
    Group child rows into:
        - vehicle_expenses
        - other_expenses
    """

    expense_claims = frappe.get_all(
        "Expense Claim",
        filters={"docstatus": 1},  # Draft only
        fields=[
            "name",
            "employee",
            "employee_name",
            "vehicle_log",
            "expense_approver",
            "approval_status",
            "company",
            "posting_date"
        ]
    )

    results = []

    for claim in expense_claims:
        doc = frappe.get_doc("Expense Claim", claim.name)

        vehicle_expenses = []
        other_expenses = []

        for row in doc.expenses:
            expense_data = {
                "description": row.description,
                "amount": row.amount,
                "sanctioned_amount": row.sanctioned_amount,
                "expense_type": row.expense_type,
                "idx": row.idx
            }

            if row.expense_type == "Vehicle Expenses":
                vehicle_expenses.append(expense_data)
            else:
                other_expenses.append(expense_data)

        results.append({
            "name": doc.name,
            "vehicle_log": doc.vehicle_log,
            "employee": doc.employee,
            "employee_name": doc.employee_name,
            "expense_approver": doc.expense_approver,
            "approval_status": doc.approval_status,
            "company": doc.company,
            "posting_date": doc.posting_date,
            "vehicle_expenses": vehicle_expenses,
            "other_expenses": other_expenses
        })

    return results


