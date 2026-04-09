import frappe
from frappe.utils import getdate, today, add_months, add_days, get_first_day, get_last_day


@frappe.whitelist()
def get_revenue_vs_budget(company=None, cost_center=None, account_type="Income"):
    """
    Optimized Revenue vs Budget API
    Filters:
        - company
        - cost_center (optional)
        - account_type: "Income" or "Expense"

    Returns:
        YTD, MTD, This Month, Last Month, This Week, Last Week
    """
    if not company:
        company = frappe.defaults.get_user_default("Company")

    today_date = getdate(today())
    periods = build_periods(today_date)

    revenue_data = get_revenue_aggregated(company, cost_center)
    budget_data = get_budget_aggregated(company, cost_center, account_type)

    result = []
    for label, (start, end) in periods.items():
        # Actual revenue sum
        actual = sum_amount_for_period(revenue_data, start, end)

        # Budget sum for same period
        budget = sum_amount_for_period(budget_data, start, end)

        # Last year same period
        last_year = sum_amount_for_period(
            revenue_data,
            add_days(start, -365),
            add_days(end, -365)
        )

        variance = actual - budget
        variance_pct = (variance / budget * 100) if budget else 0

        result.append({
            "period": label,
            "company": company,
            "cost_center": cost_center,
            "actual": actual,
            "budget": budget,
            "last_year": last_year,
            "variance": variance,
            "variance_pct": round(variance_pct, 2)
        })

    return result


# -----------------------------
# Build Periods
# -----------------------------
def build_periods(today_date):
    return {
        "YTD": (
            get_first_day(today_date.replace(month=1, day=1)),
            today_date
        ),
        "MTD": (
            get_first_day(today_date),
            today_date
        ),
        "This Month": (
            get_first_day(today_date),
            get_last_day(today_date)
        ),
        "Last Month": (
            get_first_day(add_months(today_date, -1)),
            get_last_day(add_months(today_date, -1))
        ),
        "This Week": (
            add_days(today_date, -today_date.weekday()),
            today_date
        ),
        "Last Week": (
            add_days(today_date, -today_date.weekday() - 7),
            add_days(today_date, -today_date.weekday() - 1)
        ),
    }


# -----------------------------
# Revenue Aggregated (SQL Optimized)
# -----------------------------
def get_revenue_aggregated(company, cost_center=None):
    cost_center_condition = ""
    params = [company, company]
    if cost_center:
        cost_center_condition = "AND gle.cost_center = %s"
        params.append(cost_center)

    data = frappe.db.sql(f"""
        SELECT
            gle.posting_date,
            SUM(gle.credit - gle.debit) as amount
        FROM `tabGL Entry` gle
        WHERE gle.is_cancelled = 0
        AND gle.company = %s
        AND gle.account IN (
            SELECT name FROM `tabAccount`
            WHERE root_type = 'Income'
            AND company = %s
        )
        {cost_center_condition}
        GROUP BY gle.posting_date
    """, tuple(params), as_dict=True)

    return data


# -----------------------------
# Budget Aggregated (SQL Optimized)
# -----------------------------
def get_budget_aggregated(company, cost_center=None, account_type="Income"):
    """
    Fetch budgets by fiscal year, cost center, and account type.
    Distribute annual budget equally over months if monthly_distribution = "Equally"
    """
    cost_center_condition = ""
    params = [company, account_type, company]

    if cost_center:
        cost_center_condition = "AND b.cost_center = %s"
        params.append(cost_center)

    data = frappe.db.sql(f"""
        SELECT
            fy.year_start_date,
            fy.year_end_date,
            SUM(ba.budget_amount) as annual_budget
        FROM `tabBudget` b
        JOIN `tabBudget Account` ba ON ba.parent = b.name
        JOIN `tabFiscal Year` fy ON fy.name = b.fiscal_year
        JOIN `tabAccount` acc ON acc.name = ba.account
        WHERE b.docstatus = 1
        AND b.company = %s
        AND acc.root_type = %s
        AND acc.company = %s
        {cost_center_condition}
        GROUP BY fy.year_start_date, fy.year_end_date
    """, tuple(params), as_dict=True)

    # Convert annual budget to daily allocation
    result = []
    for row in data:
        start = row.year_start_date
        end = row.year_end_date
        total_days = (getdate(end) - getdate(start)).days + 1
        daily_budget = (row.annual_budget or 0) / total_days if total_days > 0 else 0
        result.append({
            "start": start,
            "end": end,
            "daily_budget": daily_budget
        })

    return result


# -----------------------------
# Helper: Sum revenue / budget for a period
# -----------------------------
def sum_amount_for_period(data, start, end):
    total = 0
    for row in data:
        if "posting_date" in row:
            date_field = getdate(row.posting_date)
            if start <= date_field <= end:
                total += row.amount or 0
        elif "start" in row and "daily_budget" in row:
            # distribute daily budget over period
            row_start = getdate(row.start)
            row_end = getdate(row.end)
            overlap_start = max(row_start, start)
            overlap_end = min(row_end, end)
            days = (overlap_end - overlap_start).days + 1
            if days > 0:
                total += row.daily_budget * days
    return total