import frappe
from frappe.utils import flt, nowdate, add_months

@frappe.whitelist()
def get_working_capital(company, cost_center=None, from_date=None, to_date=None):
    """
    Returns Working Capital per cost center with optional date filtering.
    - company: Company name
    - cost_center: optional filter
    - from_date, to_date: optional posting date range
    """

    # Default dates: last 1 month if not provided
    if not to_date:
        to_date = nowdate()
    if not from_date:
        from_date = add_months(to_date, -1)

    filters = {"company": company, "from_date": from_date, "to_date": to_date}
    cost_center_condition = ""
    if cost_center:
        cost_center_condition = "AND gle.cost_center = %(cost_center)s"
        filters["cost_center"] = cost_center

    # 1️⃣ Current Assets
    assets_data = frappe.db.sql(f"""
        SELECT
            COALESCE(gle.cost_center, 'Unassigned') AS cost_center,
            SUM(
                CASE
                    WHEN acc.account_type IN ('Cash', 'Bank', 'Receivable', 'Current Asset')
                    THEN gle.debit - gle.credit
                    ELSE 0
                END
            ) AS current_assets
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND gle.is_cancelled = 0
            AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    assets_map = {row.cost_center: flt(row.current_assets) for row in assets_data}

    # 2️⃣ Current Liabilities
    liabilities_data = frappe.db.sql(f"""
        SELECT
            COALESCE(gle.cost_center, 'Unassigned') AS cost_center,
            SUM(
                CASE
                    WHEN acc.account_type IN ('Payable', 'Current Liability')
                    THEN gle.credit - gle.debit
                    ELSE 0
                END
            ) AS current_liabilities
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND gle.is_cancelled = 0
            AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    liabilities_map = {row.cost_center: flt(row.current_liabilities) for row in liabilities_data}

    # ----------------------------
    # 3️⃣ Calculate Working Capital & Status
    # ----------------------------
    all_ccs = set(list(assets_map.keys()) + list(liabilities_map.keys()))
    result = []

    for cc in all_ccs:
        assets = assets_map.get(cc, 0)
        liabilities = liabilities_map.get(cc, 0)
        working_capital = assets - liabilities

        # Classification
        if working_capital > 0:
            status = "Healthy"
        elif working_capital == 0:
            status = "Neutral"
        else:
            status = "Critical"

        result.append({
            "cost_center": cc,
            "current_assets": round(assets, 2),
            "current_liabilities": round(liabilities, 2),
            "working_capital": round(working_capital, 2),
            "status": status
        })

    return result