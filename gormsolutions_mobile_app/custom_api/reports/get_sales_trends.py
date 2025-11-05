import frappe
from frappe.utils import getdate, flt

@frappe.whitelist()
def get_sales_trends(company=None, cost_center=None, from_date1=None, to_date1=None, from_date2=None, to_date2=None):
    from_date1, to_date1 = getdate(from_date1), getdate(to_date1)
    from_date2, to_date2 = getdate(from_date2), getdate(to_date2)

    filters = ["si.docstatus = 1"]
    if company:
        filters.append(f"si.company = '{company}'")
    if cost_center:
        filters.append(f"si.cost_center = '{cost_center}'")
    where_clause = " AND ".join(filters)

    def fetch_sales(f, t):
        sales = frappe.db.sql(f"""
            SELECT posting_date, SUM(grand_total) AS total_sales
            FROM `tabSales Invoice` si
            WHERE posting_date BETWEEN '{f}' AND '{t}'
            AND {where_clause}
            GROUP BY posting_date
            ORDER BY posting_date ASC
        """, as_dict=1)
        total = sum([flt(d.total_sales) for d in sales])
        return sales, total

    sales1, total1 = fetch_sales(from_date1, to_date1)
    sales2, total2 = fetch_sales(from_date2, to_date2)

    return {
        "period1": {"total": total1, "sales": sales1},
        "period2": {"total": total2, "sales": sales2}
    }
