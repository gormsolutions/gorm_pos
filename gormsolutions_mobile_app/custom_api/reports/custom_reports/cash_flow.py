import frappe
import json
from frappe.utils import getdate

@frappe.whitelist()
def get_cash_flow_analysis(filters):
    """
    Cash Flow Analysis similar to ERPNext standard report.
    Shows Inflows vs Outflows per period.
    Filters:
        - from_date
        - to_date
        - company
        - cost_center (optional)
        - account (optional)
        - period: Daily/Weekly/Monthly/Quarterly/Yearly
    """
    if isinstance(filters, str):
        filters = json.loads(filters)
    f = frappe._dict(filters or {})

    period = f.get("period") or "Monthly"

    conditions = ["pe.docstatus = 1"]
    if f.get("company"):
        conditions.append("pe.company = %(company)s")
    if f.get("from_date") and f.get("to_date"):
        conditions.append("pe.posting_date BETWEEN %(from_date)s AND %(to_date)s")
    if f.get("cost_center"):
        conditions.append("pe.cost_center = %(cost_center)s")
    if f.get("account"):
        conditions.append("(pe.paid_from = %(account)s OR pe.paid_to = %(account)s)")

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            CASE
                WHEN %(period)s='Daily' THEN DATE_FORMAT(pe.posting_date,'%%Y-%%m-%%d')
                WHEN %(period)s='Weekly' THEN CONCAT(YEAR(pe.posting_date),'-W',LPAD(WEEK(pe.posting_date,1),2,'0'))
                WHEN %(period)s='Monthly' THEN DATE_FORMAT(pe.posting_date,'%%Y-%%m')
                WHEN %(period)s='Quarterly' THEN CONCAT(YEAR(pe.posting_date),'-Q',QUARTER(pe.posting_date))
                WHEN %(period)s='Yearly' THEN DATE_FORMAT(pe.posting_date,'%%Y')
            END AS period_label,
            SUM(CASE WHEN pe.payment_type='Receive' THEN pe.received_amount ELSE 0 END) AS inflow,
            SUM(CASE WHEN pe.payment_type='Pay' THEN pe.paid_amount ELSE 0 END) AS outflow
        FROM `tabPayment Entry` pe
        WHERE {where_clause}
        GROUP BY period_label
        ORDER BY period_label
    """
    data = frappe.db.sql(query, f, as_dict=True)

    # Net Cash Flow
    for d in data:
        d.net_cash_flow = (d.inflow or 0) - (d.outflow or 0)

    return data
