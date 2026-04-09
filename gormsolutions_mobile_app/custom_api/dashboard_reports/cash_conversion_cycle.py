import frappe
from frappe.utils import flt, nowdate, add_days

@frappe.whitelist()
def get_cash_conversion_cycle(company, cost_center=None, days_for_avg=90):
    """
    Returns Cash Conversion Cycle (CCC) per cost center.
    - company: Company name
    - cost_center: Optional filter
    - days_for_avg: number of days to calculate average balances
    """

    filters = {"company": company}
    cost_center_condition = ""
    if cost_center:
        cost_center_condition = "AND gle.cost_center = %(cost_center)s"
        filters["cost_center"] = cost_center

    # 1️⃣ Average Accounts Receivable (AR)
    ar_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,
            SUM(gle.debit - gle.credit) AS ar_balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND acc.account_type = 'Receivable'
            AND gle.is_cancelled = 0
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    ar_map = {row.cost_center: flt(row.ar_balance) for row in ar_data}

    # 2️⃣ Average Inventory
    inv_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,
            SUM(gle.debit - gle.credit) AS inventory_balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND acc.account_type = 'Stock'
            AND gle.is_cancelled = 0
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    inv_map = {row.cost_center: flt(row.inventory_balance) for row in inv_data}

    # 3️⃣ Average Accounts Payable (AP)
    ap_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,
            SUM(gle.credit - gle.debit) AS ap_balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND acc.account_type = 'Payable'
            AND gle.is_cancelled = 0
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    ap_map = {row.cost_center: flt(row.ap_balance) for row in ap_data}

    # 4️⃣ Calculate Daily Metrics over period
    # Average Sales (Income) over last days_for_avg
    from_date = add_days(nowdate(), -days_for_avg)
    sales_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,
            SUM(gle.credit - gle.debit) AS total_sales
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND acc.root_type = 'Income'
            AND gle.posting_date >= %(from_date)s
            AND gle.is_cancelled = 0
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, {**filters, "from_date": from_date}, as_dict=True)

    sales_map = {row.cost_center: flt(row.total_sales) for row in sales_data}

    # Average COGS over period
    cogs_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,
            SUM(gle.debit - gle.credit) AS total_cogs
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND acc.account_type = 'Cost of Goods Sold'
            AND gle.posting_date >= %(from_date)s
            AND gle.is_cancelled = 0
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, {**filters, "from_date": from_date}, as_dict=True)

    cogs_map = {row.cost_center: flt(row.total_cogs) for row in cogs_data}

    # ----------------------------
    # 5️⃣ Calculate CCC
    # ----------------------------
    result = []

    all_ccs = set(list(ar_map.keys()) + list(inv_map.keys()) + list(ap_map.keys()))

    for cc in all_ccs:
        ar = ar_map.get(cc, 0)
        inv = inv_map.get(cc, 0)
        ap = ap_map.get(cc, 0)
        total_sales = sales_map.get(cc, 0)
        total_cogs = cogs_map.get(cc, 0)

        daily_sales = total_sales / days_for_avg if total_sales else 0
        daily_cogs = total_cogs / days_for_avg if total_cogs else 0

        # Avoid division by zero
        dso = ar / daily_sales if daily_sales else 0
        dio = inv / daily_cogs if daily_cogs else 0
        dpo = ap / daily_cogs if daily_cogs else 0

        ccc = dso + dio - dpo

        result.append({
            "cost_center": cc,
            "dso_days": round(dso, 2),
            "dio_days": round(dio, 2),
            "dpo_days": round(dpo, 2),
            "ccc_days": round(ccc, 2)
        })

    return result