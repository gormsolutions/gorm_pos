# gormsolutions_mobile_app/custom_api/reports/sales_by_category.py

import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_sales_by_category(from_date, to_date, company=None, cost_center=None, customer=None, item_group=None):
    """
    Return total sales and invoice count grouped by Product Category (Item Group)
    """
    conditions = ["si.docstatus = 1"]
    values = {"from_date": from_date, "to_date": to_date}

    # Filter by exact posting date range
    conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")

    if company:
        conditions.append("si.company = %(company)s")
        values["company"] = company
    if cost_center:
        conditions.append("si.cost_center = %(cost_center)s")
        values["cost_center"] = cost_center
    if customer:
        conditions.append("si.customer = %(customer)s")
        values["customer"] = customer
    if item_group:
        conditions.append("si_item.item_group = %(item_group)s")
        values["item_group"] = item_group

    where_clause = " AND ".join(conditions)

    data = frappe.db.sql(f"""
        SELECT
            si_item.item_group AS product_category,
            SUM(si_item.amount) AS total_sales,
            COUNT(DISTINCT si.name) AS invoice_count
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` si_item
            ON si_item.parent = si.name
        WHERE {where_clause}
        GROUP BY si_item.item_group
        ORDER BY total_sales DESC
        LIMIT 50
    """, values, as_dict=True)

    for d in data:
        d.total_sales = flt(d.total_sales)

    return data
