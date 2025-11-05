import frappe

@frappe.whitelist()
def get_top_products(from_date=None, to_date=None, company=None, cost_center=None, item_code=None):
    conditions = ""
    values = {
        "from_date": from_date,
        "to_date": to_date
    }

    if company:
        conditions += " AND si.company = %(company)s"
        values["company"] = company

    if cost_center:
        conditions += " AND si_item.cost_center = %(cost_center)s"
        values["cost_center"] = cost_center

    if item_code:
        conditions += " AND si_item.item_code = %(item_code)s"
        values["item_code"] = item_code

    data = frappe.db.sql("""
        SELECT 
            si_item.item_code,
            si_item.item_name,
            SUM(si_item.base_net_amount) AS total_revenue
        FROM `tabSales Invoice Item` si_item
        JOIN `tabSales Invoice` si ON si.name = si_item.parent
        WHERE si.docstatus = 1
        AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        {conditions}
        GROUP BY si_item.item_code, si_item.item_name
        ORDER BY total_revenue DESC
        LIMIT 10
    """.format(conditions=conditions), values, as_dict=True)

    return data
