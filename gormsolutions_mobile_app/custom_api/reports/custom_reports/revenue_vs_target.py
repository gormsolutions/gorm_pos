import frappe
import json
from datetime import datetime, timedelta
import calendar

@frappe.whitelist()
def get_revenue_vs_target(filters):
    """
    Returns Revenue vs Target report data with actual SPLY.
    Filters expected as JSON string or dict:
        - from_date
        - to_date
        - company
        - cost_center (optional)
        - period: Daily / Weekly / Monthly / Quarterly / Yearly
    """
    # Parse JSON filters if needed
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = {}

    f = frappe._dict(filters or {})
    period = f.get("period") or "Monthly"

    # Build WHERE clause dynamically
    conditions = ["si.docstatus = 1"]
    if f.get("company"):
        conditions.append("si.company = %(company)s")
    if f.get("from_date") and f.get("to_date"):
        conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")
    if f.get("cost_center"):
        conditions.append("si.cost_center = %(cost_center)s")

    where_clause = "WHERE " + " AND ".join(conditions)

    # SQL query using grand_total
    query = f"""
        SELECT
            CASE
                WHEN %(period)s='Daily' THEN DATE_FORMAT(si.posting_date, '%%Y-%%m-%%d')
                WHEN %(period)s='Weekly' THEN CONCAT(YEAR(si.posting_date), '-W', WEEK(si.posting_date, 1))
                WHEN %(period)s='Monthly' THEN DATE_FORMAT(si.posting_date, '%%Y-%%m')
                WHEN %(period)s='Quarterly' THEN CONCAT(YEAR(si.posting_date), '-Q', QUARTER(si.posting_date))
                WHEN %(period)s='Yearly' THEN DATE_FORMAT(si.posting_date, '%%Y')
            END AS period_label,
            si.set_warehouse AS outlet,
            si.cost_center AS cost_center,
            SUM(si.grand_total) AS revenue
        FROM `tabSales Invoice` si
        {where_clause}
        GROUP BY period_label, si.cost_center, si.set_warehouse
        ORDER BY MIN(si.posting_date)
    """

    data = frappe.db.sql(query, f, as_dict=True)

    for d in data:
        # Fetch target
        target = frappe.db.sql("""
            SELECT SUM(target_amount)
            FROM `tabSales Target`
            WHERE company=%(company)s
              AND cost_center=%(cost_center)s
        """, {
            "company": f.get("company"),
            "cost_center": d.cost_center
        })[0][0] or 0
        d.target = target

        # Calculate SPLY (Same Period Last Year)
        sply_start, sply_end = None, None

        try:
            if period == "Daily":
                sply_start = sply_end = datetime.strptime(d.period_label, "%Y-%m-%d") - timedelta(days=365)
            elif period == "Weekly":
                year, week = map(int, d.period_label.split("-W"))
                # Use ISO calendar for consistent week handling
                sply_start = datetime.fromisocalendar(year-1, week, 1)  # Monday
                sply_end = datetime.fromisocalendar(year-1, week, 7)    # Sunday
            elif period == "Monthly":
                y, m = map(int, d.period_label.split("-"))
                sply_start = datetime(y-1, m, 1)
                sply_end = datetime(y-1, m, calendar.monthrange(y-1, m)[1])
            elif period == "Quarterly":
                y, q = d.period_label.split("-Q")
                y, q = int(y)-1, int(q)
                start_month = 3*(q-1)+1
                end_month = start_month+2
                sply_start = datetime(y, start_month, 1)
                sply_end = datetime(y, end_month, calendar.monthrange(y, end_month)[1])
            elif period == "Yearly":
                y = int(d.period_label)-1
                sply_start = datetime(y, 1, 1)
                sply_end = datetime(y, 12, 31)
        except Exception:
            sply_start = sply_end = None

        if sply_start and sply_end:
            sply = frappe.db.sql("""
                SELECT SUM(grand_total)
                FROM `tabSales Invoice`
                WHERE company=%(company)s
                  AND cost_center=%(cost_center)s
                  AND posting_date BETWEEN %(start)s AND %(end)s
                  AND docstatus = 1
            """, {
                "company": f.get("company"),
                "cost_center": d.cost_center,
                "start": sply_start,
                "end": sply_end
            })[0][0] or 0
        else:
            sply = 0

        d.sply = sply
        d.achievement = (d.revenue / d.target * 100) if d.target else 0
        d.growth = ((d.revenue - d.sply) / d.sply * 100) if d.sply else 0

    return data
