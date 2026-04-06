import frappe
from frappe.utils import flt, nowdate, add_months

@frappe.whitelist()
def get_cash_runway(company, months=6, cost_center=None):
    """
    Returns cash runway per cost center for the given company.
    - months: number of months to calculate average burn
    - cost_center: optional filter
    """

    months = int(months)
    from_date = add_months(nowdate(), -months)

    filters = {
        "company": company,
        "from_date": from_date
    }

    cost_center_condition = ""
    if cost_center:
        cost_center_condition = "AND gle.cost_center = %(cost_center)s"
        filters["cost_center"] = cost_center

    # ----------------------------
    # 1️⃣ AVAILABLE CASH BY COST CENTER
    # ----------------------------
    cash_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,
            SUM(gle.debit - gle.credit) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND gle.is_cancelled = 0
            AND acc.account_type IN ('Cash', 'Bank')
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    cash_map = {row.cost_center: flt(row.balance) for row in cash_data}

    # ----------------------------
    # 2️⃣ MONTHLY NET BURN BY COST CENTER
    # ----------------------------
    burn_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,
            DATE_FORMAT(gle.posting_date, '%%Y-%%m') AS month,
            SUM(IF(acc.root_type = 'Income', gle.credit - gle.debit, 0)) AS inflow,
            SUM(IF(acc.root_type = 'Expense', gle.debit - gle.credit, 0)) AS outflow
        FROM `tabGL Entry` gle
        INNER JOIN (
            SELECT name, root_type
            FROM `tabAccount`
            WHERE root_type IN ('Income', 'Expense')
        ) acc ON acc.name = gle.account
        WHERE
            gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.is_cancelled = 0
            {cost_center_condition}
        GROUP BY gle.cost_center, month
    """, filters, as_dict=True)

    # ----------------------------
    # Organize burn per cost center
    # ----------------------------
    burn_map = {}
    for row in burn_data:
        cc = row.cost_center
        inflow = flt(row.inflow)
        outflow = flt(row.outflow)
        net = inflow - outflow  # negative = burn

        if cc not in burn_map:
            burn_map[cc] = {"total_burn": 0, "months": 0}

        if net < 0:
            burn_map[cc]["total_burn"] += abs(net)
        burn_map[cc]["months"] += 1

    # ----------------------------
    # 3️⃣ CALCULATE RUNWAY & RISK
    # ----------------------------
    result = []
    all_ccs = set(list(cash_map.keys()) + list(burn_map.keys()))

    for cc in all_ccs:
        available_cash = cash_map.get(cc, 0)
        burn_info = burn_map.get(cc, {"total_burn": 0, "months": 0})

        avg_burn = (
            burn_info["total_burn"] / burn_info["months"]
            if burn_info["months"] else 0
        )

        # Prevent negative or invalid runway
        if available_cash <= 0 or avg_burn <= 0:
            runway = 0
        else:
            runway = available_cash / avg_burn

        # Risk classification
        if runway == 0:
            risk = "Critical"
        elif runway < 3:
            risk = "High Risk"
        elif runway < 6:
            risk = "Warning"
        else:
            risk = "Safe"

        result.append({
            "cost_center": cc,
            "available_cash": round(available_cash, 2),
            "average_monthly_burn": round(avg_burn, 2),
            "cash_runway_months": round(runway, 2),
            "risk_status": risk
        })

    return result