import frappe  # type: ignore
from frappe import _  # type: ignore
from frappe.utils import now  # type: ignore

@frappe.whitelist()
def create_self_expense(
    items=None,
    posting_date=None,
    ):
    user = frappe.session.user
    expense_setting = frappe.get_doc("Expense Settings", {"user": user})

    if not expense_setting:
        frappe.throw(_("Expense settings not found for the user."))

    # Parse items if sent as JSON string
    if isinstance(items, str):
        items = frappe.parse_json(items)

    # Create and submit Station Expenses if items exist
    if items:
        station_expense = frappe.get_doc({
            "doctype": "Station Expenses",
            "employee": expense_setting.party,
            "mode_of_payment": expense_setting.mode_of_payment,
            "date": posting_date or now(),
            "items": [
                {
                    "party_type": expense_setting.party_type,
                    "party": expense_setting.party,
                    "amount": item.get("amount"),
                    "description": item.get("description"),
                    "claim_type": item.get("claim_type")
                }
                for item in items
            ]
        })
        station_expense.insert()
        station_expense.submit()

    return {"message": _("Station Expenses submitted successfully.")}


import frappe  # type: ignore
from frappe import _  # type: ignore

@frappe.whitelist()
def get_self_expense_report(from_date=None, to_date=None):
    user = frappe.session.user

    filters = {
        "owner": user,
        "docstatus": 1 # Only fetch submitted expenses
    }

    # Apply date range filters
    if from_date and to_date:
        filters["date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["date"] = [">=", from_date]
    elif to_date:
        filters["date"] = ["<=", to_date]

    # Fetch Station Expenses created by this user
    expenses = frappe.get_all(
        "Station Expenses",
        filters=filters,
        fields=["name", "date", "mode_of_payment", "employee"]
    )

    grouped_result = {}

    for expense in expenses:
        items = frappe.get_all(
            "Expense Claim Items",
            filters={"parent": expense["name"]},
            fields=["description", "amount", "claim_type"]
        )

        total_amount = sum(item["amount"] for item in items if item.get("amount"))
        date = str(expense["date"])

        # Fetch employee_name from Employee doctype
        employee_name = ""
        if expense.get("employee"):
            employee_name = frappe.db.get_value("Employee", expense["employee"], "employee_name") or ""

        if date not in grouped_result:
            grouped_result[date] = {
                "total_amount": 0,
                "expenses": []
            }

        grouped_result[date]["expenses"].append({
            "name": expense["name"],
            "mode_of_payment": expense["mode_of_payment"],
            "employee": expense["employee"],
            "employee_name": employee_name,
            "total_amount": total_amount,
            "items": items
        })

        grouped_result[date]["total_amount"] += total_amount

    return grouped_result

@frappe.whitelist()
def get_expenses_bycost_center(from_date=None, to_date=None, cost_center=None):
    parent_cc = "Hashim Gas Limited - SE"
    current_user = frappe.session.user

    # Step 1: Get all child cost centers under the parent
    child_cost_centers = frappe.get_all(
        "Cost Center",
        filters={"parent_cost_center": parent_cc},
        pluck="name"
    )

    # Step 2: Check if the user has a restricted permission
    permitted_cost_center = frappe.get_all(
        'User Permission',
        filters={
            'user': current_user,
            'allow': 'Cost Center',
            'is_default': 1
        },
        fields=['for_value']
    )
    user_is_restricted = bool(permitted_cost_center)

    # If a specific cost center is provided
    if cost_center:
        if cost_center not in child_cost_centers:
            return {}  # Invalid cost center
        child_cost_centers = [cost_center]

    # If no specific cost center but user has a restriction
    elif user_is_restricted:
        permitted_cc = permitted_cost_center[0]['for_value']
        if permitted_cc in child_cost_centers:
            child_cost_centers = [permitted_cc]
        else:
            return {}  # User's permitted cost center is not under the parent

    # else use all child cost centers under parent_cc (default)

    filters = {}

    # Step 3: Apply date range filters
    if from_date and to_date:
        filters["date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["date"] = [">=", from_date]
    elif to_date:
        filters["date"] = ["<=", to_date]

    # Step 4: Filter by station (cost center)
    filters["station"] = ["in", child_cost_centers]

    # Step 5: Fetch Station Expenses
    expenses = frappe.get_all(
        "Station Expenses",
        filters=filters,
        fields=["name", "date", "mode_of_payment", "employee", "station"]
    )

    grouped_result = {}

    for expense in expenses:
        items = frappe.get_all(
            "Expense Claim Items",
            filters={"parent": expense["name"]},
            fields=["description", "amount", "claim_type"]
        )

        total_amount = sum(item["amount"] for item in items if item.get("amount"))
        date = str(expense["date"])
        station = expense.get("station")

        # Get employee name
        employee_name = ""
        if expense.get("employee"):
            employee_name = frappe.db.get_value("Employee", expense["employee"], "employee_name") or ""

        # Initialize date group
        if date not in grouped_result:
            grouped_result[date] = {}

        # Initialize station group
        if station not in grouped_result[date]:
            grouped_result[date][station] = {
                "total_amount": 0,
                "expenses": []
            }

        grouped_result[date][station]["expenses"].append({
            "name": expense["name"],
            "mode_of_payment": expense["mode_of_payment"],
            "employee": expense["employee"],
            "employee_name": employee_name,
            "station": station,
            "total_amount": total_amount,
            "items": items
        })

        grouped_result[date][station]["total_amount"] += total_amount

    return grouped_result
