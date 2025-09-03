import frappe  # type: ignore
from frappe import _  # type: ignore
from frappe.utils import now  # type: ignore

@frappe.whitelist()
def create_self_expense(items=None, posting_date=None):
    user = frappe.session.user

    # Get Expense Settings for current user
    expense_setting = frappe.get_value(
        "Expense Settings",
        {"user": user},
        ["party", "party_type", "company", "payable_account", "mode_of_payment", "branch"],
        as_dict=True
    )

    if not expense_setting:
        frappe.throw(_("Expense Settings not found for the user: {0}").format(user))

    # Parse items if passed as JSON string
    if isinstance(items, str):
        items = frappe.parse_json(items)

    if not items or not isinstance(items, list):
        frappe.throw(_("No valid expense items provided."))

    # Construct child items
    child_items = []
    for item in items:
        if not item.get("amount"):
            frappe.throw(_("Each item must include an 'amount'."))
        child_items.append({
            "party_type": expense_setting.party_type,
            "party": expense_setting.party,
            "amount": item.get("amount"),
            "description": item.get("description") or "",
            "claim_type": item.get("claim_type") or "General"
        })

    # Create and submit the Branch Expenses document
    branch_expense = frappe.get_doc({
        "doctype": "Branch Expenses",
        "employee": expense_setting.party,
        "station": expense_setting.branch,
        "company": expense_setting.company,
        "account": expense_setting.payable_account,
        "mode_of_payment": expense_setting.mode_of_payment,
        "date": posting_date or now(),
        "items": child_items
    })

    branch_expense.insert()
    branch_expense.submit()

    return {
        "message": _("Branch Expenses {0} submitted successfully.").format(branch_expense.name),
        "name": branch_expense.name
    }



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

# @frappe.whitelist()
# def get_expenses_bycost_center(from_date=None, to_date=None, cost_center=None):
#     # parent_cc = "Generation 7 Limited - G7L"
#     defaulf_parent_cc = frappe.db.get_value("POS Default")
#     parent_cc = defaulf_parent_cc.parent_cost_center
#     current_user = frappe.session.user

#     # Step 1: Get all child cost centers under the parent
#     child_cost_centers = frappe.get_all(
#         "Cost Center",
#         filters={"parent_cost_center": parent_cc},
#         pluck="name"
#     )

#     # Step 2: Check if the user has a restricted permission
#     permitted_cost_center = frappe.get_all(
#         'User Permission',
#         filters={
#             'user': current_user,
#             'allow': 'Cost Center',
#             'is_default': 1
#         },
#         fields=['for_value']
#     )
#     user_is_restricted = bool(permitted_cost_center)

#     # If a specific cost center is provided
#     if cost_center:
#         if cost_center not in child_cost_centers:
#             return {}  # Invalid cost center
#         child_cost_centers = [cost_center]

#     # If no specific cost center but user has a restriction
#     elif user_is_restricted:
#         permitted_cc = permitted_cost_center[0]['for_value']
#         if permitted_cc in child_cost_centers:
#             child_cost_centers = [permitted_cc]
#         else:
#             return {}  # User's permitted cost center is not under the parent

#     # else use all child cost centers under parent_cc (default)

#     filters = {"docstatus": 1}  # ✅ Only submitted Branch Expenses

#     # Step 3: Apply date range filters
#     if from_date and to_date:
#         filters["date"] = ["between", [from_date, to_date]]
#     elif from_date:
#         filters["date"] = [">=", from_date]
#     elif to_date:
#         filters["date"] = ["<=", to_date]

#     # Step 4: Filter by station (cost center)
#     filters["station"] = ["in", child_cost_centers]

#     # Step 5: Fetch Station Expenses
#     expenses = frappe.get_all(
#         "Branch Expenses",
#         filters=filters,
#         fields=["name", "date", "mode_of_payment", "employee", "station"]
#     )

#     grouped_result = {}

#     for expense in expenses:
#         items = frappe.get_all(
#             "Expense Claim Items",
#             filters={"parent": expense["name"]},
#             fields=["description", "amount", "claim_type"]
#         )

#         total_amount = sum(item["amount"] for item in items if item.get("amount"))
#         date = str(expense["date"])
#         station = expense.get("station")

#         # Get employee name
#         employee_name = ""
#         if expense.get("employee"):
#             employee_name = frappe.db.get_value("Employee", expense["employee"], "employee_name") or ""

#         # Initialize date group
#         if date not in grouped_result:
#             grouped_result[date] = {}

#         # Initialize station group
#         if station not in grouped_result[date]:
#             grouped_result[date][station] = {
#                 "total_amount": 0,
#                 "expenses": []
#             }

#         grouped_result[date][station]["expenses"].append({
#             "name": expense["name"],
#             "mode_of_payment": expense["mode_of_payment"],
#             "employee": expense["employee"],
#             "employee_name": employee_name,
#             "station": station,
#             "total_amount": total_amount,
#             "items": items
#         })

#         grouped_result[date][station]["total_amount"] += total_amount

#     return grouped_result

@frappe.whitelist()
def get_expenses_bycost_center(from_date=None, to_date=None, cost_center=None):
    # ✅ Fetch parent cost center correctly
    parent_cc = frappe.db.get_value("POS Default", None, "parent_cost_center")
    if not parent_cc:
        frappe.throw("No Parent Cost Center found in POS Default")

    current_user = frappe.session.user

    # Step 1: Get all child cost centers under the parent
    child_cost_centers = frappe.get_all(
        "Cost Center",
        filters={"parent_cost_center": parent_cc},
        pluck="name"
    )

    # Step 2: Check if the user has a restricted permission
    permitted_cost_center = frappe.get_all(
        "User Permission",
        filters={
            "user": current_user,
            "allow": "Cost Center",
            "is_default": 1
        },
        fields=["for_value"]
    )
    user_is_restricted = bool(permitted_cost_center)

    # Step 3: Handle cost center restrictions
    if cost_center:
        if cost_center not in child_cost_centers:
            return {}  # Invalid cost center
        child_cost_centers = [cost_center]

    elif user_is_restricted:
        permitted_cc = permitted_cost_center[0]["for_value"]
        if permitted_cc in child_cost_centers:
            child_cost_centers = [permitted_cc]
        else:
            return {}  # User's permitted cost center is not under the parent

    # Step 4: Prepare filters
    filters = {"docstatus": 1}  # ✅ Only submitted Branch Expenses

    if from_date and to_date:
        filters["date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["date"] = [">=", from_date]
    elif to_date:
        filters["date"] = ["<=", to_date]

    filters["station"] = ["in", child_cost_centers]

    # Step 5: Fetch Branch Expenses
    expenses = frappe.get_all(
        "Branch Expenses",
        filters=filters,
        fields=["name", "date", "mode_of_payment", "employee", "station"]
    )

    grouped_result = {}

    # Step 6: Process and group results
    for expense in expenses:
        items = frappe.get_all(
            "Expense Claim Items",
            filters={"parent": expense["name"]},
            fields=["description", "amount", "claim_type"]
        )

        total_amount = sum(item.get("amount", 0) for item in items)
        date = str(expense["date"])
        station = expense.get("station")

        employee_name = ""
        if expense.get("employee"):
            employee_name = frappe.db.get_value("Employee", expense["employee"], "employee_name") or ""

        if date not in grouped_result:
            grouped_result[date] = {}

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


import frappe

@frappe.whitelist()
def get_expense_claim_types():
    """Return all Expense Claim Types."""
    claim_types = frappe.get_all(
        "Expense Claim Type",
        fields=["name"]
    )
    return claim_types