import frappe
from frappe.utils import getdate, flt, add_months, add_years

@frappe.whitelist()
def get_procurement_trends(company=None, supplier=None, item_code=None, cost_center=None, from_date=None, to_date=None):
    # Default to last 3 months if not provided
    to_date = getdate(to_date) if to_date else getdate()
    from_date = getdate(from_date) if from_date else add_months(to_date, -2)

    filters = ["pi.docstatus = 1"]
    if company:
        filters.append(f"pi.company = '{company}'")
    if supplier:
        filters.append(f"pi.supplier = '{supplier}'")
    if item_code:
        filters.append(f"pid.item_code = '{item_code}'")
    if cost_center:
        filters.append(f"pi.cost_center = '{cost_center}'")

    where_clause = " AND ".join(filters)

    # --- Current period ---
    current_period = frappe.db.sql(f"""
        SELECT SUM(pid.amount) AS total_amount,
               DATE_FORMAT(pi.posting_date, '%Y-%m') AS period
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pid ON pid.parent = pi.name
        WHERE pi.posting_date BETWEEN '{from_date}' AND '{to_date}'
        AND {where_clause}
        GROUP BY DATE_FORMAT(pi.posting_date, '%Y-%m')
        ORDER BY period
    """, as_dict=1)

    # --- MoM (previous month) ---
    from_date_mom = add_months(from_date, -1)
    to_date_mom = add_months(to_date, -1)
    mom_period = frappe.db.sql(f"""
        SELECT SUM(pid.amount) AS total_amount,
               DATE_FORMAT(pi.posting_date, '%Y-%m') AS period
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pid ON pid.parent = pi.name
        WHERE pi.posting_date BETWEEN '{from_date_mom}' AND '{to_date_mom}'
        AND {where_clause}
        GROUP BY DATE_FORMAT(pi.posting_date, '%Y-%m')
        ORDER BY period
    """, as_dict=1)

    # --- SPLY (same period last year) ---
    from_date_sply = add_years(from_date, -1)
    to_date_sply = add_years(to_date, -1)
    sply_period = frappe.db.sql(f"""
        SELECT SUM(pid.amount) AS total_amount,
               DATE_FORMAT(pi.posting_date, '%Y-%m') AS period
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pid ON pid.parent = pi.name
        WHERE pi.posting_date BETWEEN '{from_date_sply}' AND '{to_date_sply}'
        AND {where_clause}
        GROUP BY DATE_FORMAT(pi.posting_date, '%Y-%m')
        ORDER BY period
    """, as_dict=1)

    # --- Combine results ---
    trends = {}
    for d in current_period:
        trends[d['period']] = {'current': flt(d['total_amount']), 'mom': 0, 'sply': 0}

    for d in mom_period:
        # Map previous month to current period
        prev_period = add_months(getdate(d['period'] + "-01"), 1).strftime("%Y-%m")
        if prev_period in trends:
            trends[prev_period]['mom'] = flt(d['total_amount'])

    for d in sply_period:
        # Map last year same period to current period
        sply_period_str = add_years(getdate(d['period'] + "-01"), 1).strftime("%Y-%m")
        if sply_period_str in trends:
            trends[sply_period_str]['sply'] = flt(d['total_amount'])

    # Only include periods with any transactions
    filtered_trends = {k: v for k, v in trends.items() if v['current'] > 0 or v['mom'] > 0 or v['sply'] > 0}

    return filtered_trends
