import frappe

@frappe.whitelist()
def get_budget_variance(company=None, cost_center=None):
    """
    Budget Variance Report
    Compares actual expenses and revenues to the planned amounts.

    Filters:
        - company (defaults to user default)
        - cost_center (optional)

    Returns:
        List of accounts with cost center, actual, budget, variance, and variance %
    """

    if not company:
        company = frappe.defaults.get_user_default("Company")

    # Cost Center filters
    cost_center_condition_gl = ""
    cost_center_condition_budget = ""
    params_gl = [company, company]
    params_budget = [company, company]

    if cost_center:
        cost_center_condition_gl = "AND gle.cost_center = %s"
        cost_center_condition_budget = "AND b.cost_center = %s"
        params_gl.append(cost_center)
        params_budget.append(cost_center)

    # 1️⃣ Fetch Actuals per Account + Cost Center (Expenses + Income)
    actuals = frappe.db.sql(f"""
        SELECT gle.account, gle.cost_center, SUM(gle.debit - gle.credit) as actual
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0
        AND gle.company = %s
        AND acc.company = %s
        AND acc.root_type IN ('Expense', 'Income')
        {cost_center_condition_gl}
        GROUP BY gle.account, gle.cost_center
    """, tuple(params_gl), as_dict=True)

    # 2️⃣ Fetch Budgets per Account + Cost Center
    budgets = frappe.db.sql(f"""
        SELECT ba.account, b.cost_center, SUM(ba.budget_amount) as budget
        FROM `tabBudget` b
        JOIN `tabBudget Account` ba ON ba.parent = b.name
        JOIN `tabAccount` acc ON acc.name = ba.account
        WHERE b.docstatus = 1
        AND b.company = %s
        AND acc.root_type IN ('Expense', 'Income')
        AND acc.company = %s
        {cost_center_condition_budget}
        GROUP BY ba.account, b.cost_center
    """, tuple(params_budget), as_dict=True)

    # 3️⃣ Merge Actuals + Budgets by account + cost center
    accounts_map = {}
    for row in actuals:
        key = (row.account, row.cost_center)
        accounts_map[key] = {"actual": row.actual, "budget": 0}

    for row in budgets:
        key = (row.account, row.cost_center)
        if key in accounts_map:
            accounts_map[key]["budget"] = row.budget
        else:
            accounts_map[key] = {"actual": 0, "budget": row.budget}

    # 4️⃣ Prepare result with variance
    result = []
    for (account, cc), vals in accounts_map.items():
        actual = vals.get("actual", 0)
        budget = vals.get("budget", 0)
        variance = actual - budget
        variance_pct = (variance / budget * 100) if budget else 0

        result.append({
            "account": account,
            "cost_center": cc or "Unassigned",
            "actual": actual,
            "budget": budget,
            "variance": variance,
            "variance_pct": round(variance_pct, 2)
        })

    # Sort by largest variance
    result.sort(key=lambda x: abs(x["variance"]), reverse=True)

    return result