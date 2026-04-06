import frappe
from frappe.utils import flt, nowdate, add_months

@frappe.whitelist()
def get_trend_line(company, metric='revenue', from_date=None, to_date=None, cost_center=None):
    """
    Returns trend data for a metric over time.
    metric: 'revenue', 'cash_flow', 'net_profit'
    """
    if not to_date:
        to_date = nowdate()
    if not from_date:
        from_date = add_months(to_date, -6)  # default last 6 months

    filters = {"company": company, "from_date": from_date, "to_date": to_date}
    cc_condition = ""
    if cost_center:
        filters["cost_center"] = cost_center
        cc_condition = "AND gle.cost_center = %(cost_center)s"

    if metric == 'revenue':
        account_filter = "acc.root_type='Income'"
        value_calc = "gle.credit - gle.debit"
    elif metric == 'cash_flow':
        account_filter = "acc.account_type IN ('Cash','Bank')"
        value_calc = "gle.debit - gle.credit"
    elif metric == 'net_profit':
        account_filter = "(acc.root_type='Income' OR acc.root_type='Expense')"
        value_calc = "CASE WHEN acc.root_type='Income' THEN gle.credit - gle.debit ELSE -(gle.debit - gle.credit) END"
    else:
        return []

    trend = frappe.db.sql(f"""
        SELECT
            DATE_FORMAT(gle.posting_date, '%%Y-%%m') AS period,
            SUM({value_calc}) AS value
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE gle.company=%(company)s
        AND {account_filter}
        AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND gle.is_cancelled=0
        {cc_condition}
        GROUP BY period
        ORDER BY period ASC
    """, filters, as_dict=True)

    return trend


@frappe.whitelist()
def get_gauge_progress(company, metric='revenue', target=1000000, cost_center=None, from_date=None, to_date=None):
    # Convert target to float if it's a string
    if isinstance(target, str):
        try:
            target = float(target)
        except ValueError:
            target = 1000000  # default value if conversion fails
    
    filters = {"company": company}
    conditions = []

    if cost_center:
        filters["cost_center"] = cost_center
        conditions.append("gle.cost_center = %(cost_center)s")

    if from_date:
        filters["from_date"] = from_date
        conditions.append("gle.posting_date >= %(from_date)s")

    if to_date:
        filters["to_date"] = to_date
        conditions.append("gle.posting_date <= %(to_date)s")

    # Metric logic
    if metric == 'revenue':
        value_calc = "gle.credit - gle.debit"
        account_filter = "acc.root_type = 'Income'"
    elif metric == 'cash_flow':
        value_calc = "gle.debit - gle.credit"
        account_filter = "acc.account_type IN ('Cash','Bank')"
    else:
        return {}

    # Combine conditions
    extra_conditions = ""
    if conditions:
        extra_conditions = " AND " + " AND ".join(conditions)

    result = frappe.db.sql(f"""
        SELECT SUM({value_calc}) AS value
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE gle.company = %(company)s
        AND {account_filter}
        AND gle.is_cancelled = 0
        {extra_conditions}
    """, filters, as_dict=True)

    actual = flt(result[0].value) if result and result[0].value else 0
    
    # Now target is definitely a float
    percent = round((actual / target) * 100, 2) if target else 0

    return {
        "metric": metric,
        "actual": actual,
        "target": target,
        "progress_pct": percent,
        "from_date": from_date,
        "to_date": to_date
    }

@frappe.whitelist()
def get_profit_heatmap(company, dimension='cost_center', from_date=None, to_date=None):
    if not to_date:
        to_date = nowdate()
    if not from_date:
        from_date = add_months(to_date, -6)

    filters = {"company": company, "from_date": from_date, "to_date": to_date}

    result = frappe.db.sql(f"""
        SELECT
            COALESCE(gle.{dimension}, 'Unassigned') AS key_dim,
            SUM(
                CASE WHEN acc.root_type='Income' THEN gle.credit - gle.debit
                     WHEN acc.root_type='Expense' THEN -(gle.debit - gle.credit)
                     ELSE 0 END
            ) AS net_profit
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.company=%(company)s
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND gle.is_cancelled=0
        GROUP BY key_dim
        ORDER BY net_profit DESC
    """, filters, as_dict=True)

    return result



def compute_traffic_light(actual, target):
    """Return RAG status based on actual vs target"""
    actual = flt(actual)
    target = flt(target)
    ratio = actual / target if target else 0
    if ratio >= 0.9:
        return "Green"
    elif ratio >= 0.7:
        return "Amber"
    else:
        return "Red"

@frappe.whitelist()
def get_kpis_with_rag(company, from_date=None, to_date=None, cost_center=None, targets=None):
    """
    Returns all KPIs dynamically with RAG status.
    
    Parameters:
    - company: company name
    - from_date, to_date: optional date range
    - cost_center: optional
    - targets: optional dict of KPI targets, e.g. {"revenue":1000000,"net_profit":500000}
    
    Returns:
    - List of KPI results with metric name, value, target, and status
    """

    if not to_date:
        to_date = nowdate()
    if not from_date:
        from_date = add_months(to_date, -1)

    results = []

    targets = targets or {}

    # -----------------------------
    # 1️⃣ Revenue
    # -----------------------------
    filters = {"company": company, "from_date": from_date, "to_date": to_date}
    cc_condition = f"AND gle.cost_center = %(cost_center)s" if cost_center else ""
    if cost_center:
        filters["cost_center"] = cost_center

    revenue = frappe.db.sql(f"""
        SELECT SUM(gle.credit - gle.debit) AS value
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE gle.company=%(company)s
          AND acc.root_type='Income'
          AND gle.is_cancelled=0
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          {cc_condition}
    """, filters, as_dict=True)
    revenue_value = flt(revenue[0].value) if revenue else 0
    results.append({
        "metric": "Revenue",
        "actual": revenue_value,
        "target": targets.get("revenue", 0),
        "status": compute_traffic_light(revenue_value, targets.get("revenue", 0))
    })

    # -----------------------------
    # 2️⃣ Net Profit
    # -----------------------------
    net_profit_data = frappe.db.sql(f"""
        SELECT SUM(
            CASE WHEN acc.root_type='Income' THEN gle.credit - gle.debit
                 ELSE -(gle.debit - gle.credit)
            END
        ) AS value
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE gle.company=%(company)s
          AND (acc.root_type='Income' OR acc.root_type='Expense')
          AND gle.is_cancelled=0
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          {cc_condition}
    """, filters, as_dict=True)
    net_profit_value = flt(net_profit_data[0].value) if net_profit_data else 0
    results.append({
        "metric": "Net Profit",
        "actual": net_profit_value,
        "target": targets.get("net_profit", 0),
        "status": compute_traffic_light(net_profit_value, targets.get("net_profit", 0))
    })

    # -----------------------------
    # 3️⃣ Working Capital
    # -----------------------------
    # Current Assets
    assets_data = frappe.db.sql(f"""
        SELECT SUM(
            CASE WHEN acc.account_type IN ('Cash', 'Bank', 'Receivable', 'Current Asset')
            THEN gle.debit - gle.credit ELSE 0 END
        ) AS value
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE gle.company=%(company)s
          AND gle.is_cancelled=0
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          {cc_condition}
    """, filters, as_dict=True)
    current_assets = flt(assets_data[0].value) if assets_data else 0

    # Current Liabilities
    liabilities_data = frappe.db.sql(f"""
        SELECT SUM(
            CASE WHEN acc.account_type IN ('Payable', 'Current Liability')
            THEN gle.credit - gle.debit ELSE 0 END
        ) AS value
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE gle.company=%(company)s
          AND gle.is_cancelled=0
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          {cc_condition}
    """, filters, as_dict=True)
    current_liabilities = flt(liabilities_data[0].value) if liabilities_data else 0

    working_capital_value = current_assets - current_liabilities
    results.append({
        "metric": "Working Capital",
        "actual": working_capital_value,
        "target": targets.get("working_capital", 0),
        "status": compute_traffic_light(working_capital_value, targets.get("working_capital", 0))
    })

    # -----------------------------
    # 4️⃣ Quick Ratio (Acid Test)
    # -----------------------------
    liquid_assets_value = current_assets  # Cash+Bank+Receivables already calculated
    quick_ratio_value = (liquid_assets_value / current_liabilities) if current_liabilities else 0
    results.append({
        "metric": "Quick Ratio",
        "actual": round(quick_ratio_value,2),
        "target": targets.get("quick_ratio", 1),  # Usually 1 is ideal
        "status": compute_traffic_light(quick_ratio_value, targets.get("quick_ratio", 1))
    })

    # Add more KPIs here as needed: Gross Profit Margin, CCC, Cash Flow, Cash Runway, etc.

    return results