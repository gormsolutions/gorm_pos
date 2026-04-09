import frappe
from frappe.utils import flt

@frappe.whitelist()
def budget_vs_actual(company, from_date, to_date, cost_center=None):
    """Budget vs Actual Spend per Account (ERPNext v15)"""

    # --- Fetch Fiscal Year for filter ---
    fiscal_year = frappe.db.get_value(
        "Fiscal Year",
        {"year_start_date": ("<=", from_date), "year_end_date": (">=", to_date)},
        "name"
    )

    if not fiscal_year:
        frappe.throw("Fiscal Year not found for selected date range")

    # --- Budget Data (Account wise) ---
    cost_filter = ""
    params = [company, fiscal_year]
    if cost_center:
        cost_filter = " AND ba.cost_center = %s "
        params.append(cost_center)

    budget_data = frappe.db.sql(f"""
        SELECT ba.account, SUM(ba.budget_amount) AS budget
        FROM `tabBudget Account` ba
        JOIN `tabBudget` b ON ba.parent = b.name
        WHERE b.docstatus = 1
          AND b.company = %s
          AND b.fiscal_year = %s
          {cost_filter}
        GROUP BY ba.account
    """, params, as_dict=True)

    budget_map = {d.account: flt(d.budget) for d in budget_data}

    # --- Actual Spend from Purchase Invoice ---
    cost_filter_actual = ""
    params_actual = [company, from_date, to_date]
    if cost_center:
        cost_filter_actual = " AND pii.cost_center = %s "
        params_actual.append(cost_center)

    actual_data = frappe.db.sql(f"""
        SELECT pii.expense_account AS account, SUM(pii.amount) AS actual
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pii.parent = pi.name
        WHERE pi.docstatus = 1
          AND pi.company = %s
          AND pi.posting_date BETWEEN %s AND %s
          {cost_filter_actual}
        GROUP BY pii.expense_account
    """, params_actual, as_dict=True)

    # --- Merge Budget + Actual ---
    result = []

    for row in actual_data:
        acc = row.account or "Unspecified Account"
        budget = budget_map.get(acc, 0)
        actual = flt(row.actual)
        variance = budget - actual
        variance_percent = ((variance / budget) * 100) if budget else 0

        result.append({
            "category": acc,
            "budget": budget,
            "actual": actual,
            "variance": variance,
            "variance_percent": variance_percent
        })

    # Add budget rows with no spend
    for acc, budget in budget_map.items():
        if acc not in [r["category"] for r in result]:
            result.append({
                "category": acc,
                "budget": budget,
                "actual": 0,
                "variance": budget,
                "variance_percent": 100
            })

    # Sort high spend first
    result.sort(key=lambda x: x["actual"], reverse=True)

    return result
