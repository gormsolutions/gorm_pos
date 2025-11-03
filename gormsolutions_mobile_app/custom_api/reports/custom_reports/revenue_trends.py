import frappe
import json
from frappe.utils import getdate
from datetime import datetime, timedelta
import calendar

@frappe.whitelist()
def get_yoy_mom_revenue(filters):
    """
    YoY & MoM Revenue Trends with Cost Center
    Filters:
        - from_date
        - to_date
        - company
        - customer (optional)
        - cost_center (optional)
        - period: Daily/Weekly/Monthly/Quarterly/Yearly
    """
    if isinstance(filters, str):
        filters = json.loads(filters)

    f = frappe._dict(filters or {})
    period = f.get("period") or "Monthly"

    # Base conditions
    conditions = ["si.docstatus = 1"]
    if f.get("company"):
        conditions.append("si.company = %(company)s")
    if f.get("from_date") and f.get("to_date"):
        conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")
    if f.get("customer"):
        conditions.append("si.customer = %(customer)s")
    if f.get("cost_center"):
        conditions.append("si.cost_center = %(cost_center)s")

    where_clause = " AND ".join(conditions)

    # Query Sales Invoice totals per period + cost center
    query = f"""
        SELECT
            CASE
                WHEN %(period)s='Daily' THEN DATE_FORMAT(si.posting_date,'%%Y-%%m-%%d')
                WHEN %(period)s='Weekly' THEN CONCAT(YEAR(si.posting_date),'-W',LPAD(WEEK(si.posting_date,1),2,'0'))
                WHEN %(period)s='Monthly' THEN DATE_FORMAT(si.posting_date,'%%Y-%%m')
                WHEN %(period)s='Quarterly' THEN CONCAT(YEAR(si.posting_date),'-Q',QUARTER(si.posting_date))
                WHEN %(period)s='Yearly' THEN DATE_FORMAT(si.posting_date,'%%Y')
            END AS period_label,
            si.cost_center,
            SUM(si.grand_total) AS revenue
        FROM `tabSales Invoice` si
        WHERE {where_clause}
        GROUP BY period_label, si.cost_center
        ORDER BY period_label
    """

    data = frappe.db.sql(query, f, as_dict=True)

    # Compute MoM and YoY growth per cost center
    prev_period_revenue = {}
    for d in data:
        key = d.cost_center or 'All'
        # MoM
        if period == "Monthly":
            y, m = map(int, d.period_label.split('-'))
            prev_month = datetime(y, m, 1) - timedelta(days=1)
            prev_key = f"{prev_month.year}-{prev_month.month:02d}-{key}"
        elif period == "Yearly":
            prev_key = f"{int(d.period_label)-1}-{key}"
        else:
            prev_key = None

        prev_rev = prev_period_revenue.get(prev_key, 0) if prev_key else 0
        d.mom_growth = ((d.revenue - prev_rev) / prev_rev * 100) if prev_rev else 0

        # YoY
        if period in ["Monthly", "Quarterly"]:
            y, rest = map(int, d.period_label.split('-')[0:2])
            yoy_key = f"{y-1}-{rest:02d}-{key}"
			
        elif period == "Yearly":
            yoy_key = f"{int(d.period_label)-1}-{key}"
        else:
            yoy_key = None

        yoy_rev = prev_period_revenue.get(yoy_key, 0) if yoy_key else 0
        d.yoy_growth = ((d.revenue - yoy_rev) / yoy_rev * 100) if yoy_rev else 0

        prev_period_revenue[f"{d.period_label}-{key}"] = d.revenue

    return data
