import frappe
from frappe.utils import nowdate, get_first_day, get_last_day

@frappe.whitelist()
def get_sales_person_monthly_data(sales_person_target=None):
    """
    Fetch Sales Person Targets and their monthly Sales Invoices.
    If sales_person_target is not provided, returns data for all targets.
    """

    # Get date range for this month
    start_date = get_first_day(nowdate())
    end_date = get_last_day(nowdate())

    # If a single Sales Person Target is passed, just fetch that one
    if sales_person_target:
        targets = [frappe.get_doc("Sales Person Targets", sales_person_target)]
    else:
        # Otherwise, fetch all active (not disabled) targets
        targets = frappe.get_all(
            "Sales Person Targets",
            filters={"dissable": 0},  # assuming 'dissable' = disabled flag
            fields=["name"]
        )
        targets = [frappe.get_doc("Sales Person Targets", t.name) for t in targets]

    data = []

    for target in targets:
        user = target.user
        company = target.company
        target_amount = target.target_amount

        # Fetch Sales Invoices for this user in this month
        invoices = frappe.db.get_all(
            "Sales Invoice",
            filters={
                "owner": user,
                "company": company,
                "posting_date": ["between", [start_date, end_date]],
                "docstatus": 1  # Only submitted invoices
            },
            fields=["name", "grand_total", "posting_date"]
        )

        total_sales = sum(inv.get("grand_total", 0) for inv in invoices)

        data.append({
            "sales_person": target.employee_name,
            "user": user,
            "company": company,
            "target_amount": target_amount,
            "total_sales": total_sales,
            "invoices": invoices
        })

    return data

# import frappe
# from frappe.utils import nowdate, get_first_day, get_last_day

# @frappe.whitelist()
# def get_sales_person_monthly_data(sales_person_target=None):
#     """
#     Fetch Sales Person Targets and their monthly Sales Invoices.
#     If sales_person_target is not provided, returns data for the logged-in user only.
#     """

#     logged_in_user = frappe.session.user

#     # Get date range for this month
#     start_date = get_first_day(nowdate())
#     end_date = get_last_day(nowdate())

#     # If a single Sales Person Target is passed, just fetch that one
#     if sales_person_target:
#         targets = [frappe.get_doc("Sales Person Targets", sales_person_target)]
#     else:
#         # Fetch only active targets for the logged-in user
#         targets = frappe.get_all(
#             "Sales Person Targets",
#             filters={
#                 "dissable": 0,
#                 "user": logged_in_user
#             },
#             fields=["name"]
#         )
#         targets = [frappe.get_doc("Sales Person Targets", t.name) for t in targets]

#     data = []

#     for target in targets:
#         user = target.user
#         company = target.company
#         target_amount = target.target_amount

#         # Fetch Sales Invoices for this user in this month
#         invoices = frappe.db.get_all(
#             "Sales Invoice",
#             filters={
#                 "owner": user,
#                 "company": company,
#                 "posting_date": ["between", [start_date, end_date]],
#                 "docstatus": 1  # Only submitted invoices
#             },
#             fields=["name", "grand_total", "posting_date"]
#         )

#         total_sales = sum(inv.get("grand_total", 0) for inv in invoices)

#         data.append({
#             "sales_person": target.employee_name,
#             "user": user,
#             "company": company,
#             "target_amount": target_amount,
#             "total_sales": total_sales,
#             "invoices": invoices
#         })

#     return data
