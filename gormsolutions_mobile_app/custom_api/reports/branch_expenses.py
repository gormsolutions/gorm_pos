import frappe

@frappe.whitelist()
def get_branch_expenses(owner=None, from_date=None, to_date=None):
    """
    Fetch Branch Expenses with optional filters:
        - owner (email)
        - from_date (YYYY-MM-DD)
        - to_date (YYYY-MM-DD)
    
    Returns Branch Expenses with child Expense Claim Items.
    """

    filters = {"docstatus": 1}

    # Optional owner filter
    if owner:
        filters["owner"] = owner
    
    # Optional date filters
    if from_date and to_date:
        filters["date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["date"] = [">=", from_date]
    elif to_date:
        filters["date"] = ["<=", to_date]

    docs = frappe.get_all(
        "Branch Expenses",
        filters=filters,
        fields=[
            "name", "owner", "employee", "employee_name", "date",
            "grand_total", "mode_of_payment", "company", "station", "account"
        ],
        order_by="date desc"
    )

    result = []
    for d in docs:
        doc = frappe.get_doc("Branch Expenses", d.name)

        result.append({
            "name": doc.name,
            "owner": doc.owner,
            "employee": doc.employee,
            "employee_name": doc.employee_name,
            "date": doc.date,
            "mode_of_payment": doc.mode_of_payment,
            "grand_total": doc.grand_total,
            "company": doc.company,
            "station": doc.station,
            "account": doc.account,
            "items": [
                {
                    "party_type": i.party_type,
                    "party": i.party,
                    "claim_type": i.claim_type,
                    "amount": i.amount,
                    "description": i.description
                }
                for i in doc.items
            ]
        })

    return result
