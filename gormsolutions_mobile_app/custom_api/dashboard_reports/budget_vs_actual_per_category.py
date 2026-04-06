import frappe

@frappe.whitelist()
def get_budget_vs_actual_per_category(company=None, account_type="Expense"):
    """
    Returns Budget vs Actual spend summary:
    1. Overall total
    2. Grouped by Cost Center
    Filters:
        - company
        - account_type: "Income" or "Expense"
    """

    if not company:
        company = frappe.defaults.get_user_default("Company")

    # -----------------------------
    # Overall total
    # -----------------------------
    overall_actual = frappe.db.sql(f"""
        SELECT SUM(gle.debit - gle.credit)
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0
        AND gle.company = %s
        AND acc.company = %s
        AND acc.root_type = %s
    """, (company, company, account_type))[0][0] or 0

    overall_budget = frappe.db.sql(f"""
        SELECT SUM(ba.budget_amount)
        FROM `tabBudget` b
        JOIN `tabBudget Account` ba ON ba.parent = b.name
        JOIN `tabAccount` acc ON acc.name = ba.account
        WHERE b.docstatus = 1
        AND b.company = %s
        AND acc.company = %s
        AND acc.root_type = %s
    """, (company, company, account_type))[0][0] or 0

    overall_variance = overall_actual - overall_budget
    overall_variance_pct = (overall_variance / overall_budget * 100) if overall_budget else 0

    overall = {
        "level": "Overall",
        "actual": overall_actual,
        "budget": overall_budget,
        "variance": overall_variance,
        "variance_pct": round(overall_variance_pct, 2)
    }

    # -----------------------------
    # Group by Cost Center
    # -----------------------------
    grouped_actuals = frappe.db.sql(f"""
        SELECT gle.cost_center, SUM(gle.debit - gle.credit)
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0
        AND gle.company = %s
        AND acc.company = %s
        AND acc.root_type = %s
        GROUP BY gle.cost_center
    """, (company, company, account_type), as_dict=True)

    grouped_budgets = frappe.db.sql(f"""
        SELECT b.cost_center, SUM(ba.budget_amount)
        FROM `tabBudget` b
        JOIN `tabBudget Account` ba ON ba.parent = b.name
        JOIN `tabAccount` acc ON acc.name = ba.account
        WHERE b.docstatus = 1
        AND b.company = %s
        AND acc.company = %s
        AND acc.root_type = %s
        GROUP BY b.cost_center
    """, (company, company, account_type), as_dict=True)

    # Merge by cost_center
    cost_center_map = {}
    for row in grouped_actuals:
        cost_center_map.setdefault(row.cost_center, {})
        cost_center_map[row.cost_center]["actual"] = row["SUM(gle.debit - gle.credit)"] or 0

    for row in grouped_budgets:
        cost_center_map.setdefault(row.cost_center, {})
        cost_center_map[row.cost_center]["budget"] = row["SUM(ba.budget_amount)"] or 0

    cost_centers = []
    for cc, vals in cost_center_map.items():
        actual = vals.get("actual", 0)
        budget = vals.get("budget", 0)
        variance = actual - budget
        variance_pct = (variance / budget * 100) if budget else 0
        cost_centers.append({
            "level": cc or "Unassigned",
            "actual": actual,
            "budget": budget,
            "variance": variance,
            "variance_pct": round(variance_pct, 2)
        })

    return {
        "overall": overall,
        "by_cost_center": cost_centers
    }