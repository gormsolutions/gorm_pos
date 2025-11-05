import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_performance(from_date, to_date, company=None, sales_partner=None, cost_center=None, customer=None):
    """
    Return Sales Partner / Cost Center / Customer Performance
    """
    conditions = ["si.docstatus = 1"]
    values = {"from_date": from_date, "to_date": to_date}

    # Filter by exact posting date range
    conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")

    if company:
        conditions.append("si.company = %(company)s")
        values["company"] = company
    if sales_partner:
        conditions.append("si.sales_partner = %(sales_partner)s")
        values["sales_partner"] = sales_partner
    if cost_center:
        conditions.append("si.cost_center = %(cost_center)s")
        values["cost_center"] = cost_center
    if customer:
        conditions.append("si.customer = %(customer)s")
        values["customer"] = customer

    where_clause = " AND ".join(conditions)

    data = frappe.db.sql(f"""
        SELECT
            si.sales_partner AS sales_partner,
            si.cost_center AS cost_center,
            si.customer AS customer,
            SUM(si.grand_total) AS total_sales,
            COUNT(si.name) AS invoice_count
        FROM `tabSales Invoice` si
        WHERE {where_clause}
        GROUP BY si.sales_partner, si.cost_center, si.customer
        ORDER BY total_sales DESC
        LIMIT 50
    """, values, as_dict=True)

    for d in data:
        d.total_sales = flt(d.total_sales)

    return data
