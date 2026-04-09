import frappe
from frappe import _

@frappe.whitelist()
def get_revenue_by_outlet(start, end, company=None):
    """
    Returns revenue grouped by cost center
    """

    conditions = """
        docstatus = 1
        AND posting_date BETWEEN %(start)s AND %(end)s
    """

    if company:
        conditions += " AND company = %(company)s"

    query = f"""
        SELECT
            cost_center AS originating_outlet,
            SUM(grand_total) AS total_sales
        FROM
            `tabSales Invoice`
        WHERE
            {conditions}
        GROUP BY
            cost_center
        ORDER BY
            total_sales DESC
    """

    data = frappe.db.sql(
        query,
        {
            "start": start,
            "end": end,
            "company": company
        },
        as_dict=True
    )

    return {
        "status": "success",
        "data": data
    }
