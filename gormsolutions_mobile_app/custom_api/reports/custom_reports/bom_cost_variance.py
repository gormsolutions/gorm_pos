import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_bom_cost_variance(from_date, to_date, company=None, cost_center=None, item=None):
    """
    Return BOM Cost Variance for manufactured items
    """
    conditions = ["se.docstatus = 1"]
    values = {"from_date": from_date, "to_date": to_date}

    conditions.append("se.posting_date BETWEEN %(from_date)s AND %(to_date)s")

    if company:
        conditions.append("se.company = %(company)s")
        values["company"] = company
    if cost_center:
        conditions.append("se_item.cost_center = %(cost_center)s")
        values["cost_center"] = cost_center
    if item:
        conditions.append("se_item.item_code = %(item)s")
        values["item"] = item

    where_clause = " AND ".join(conditions)

    print("BOM Cost Variance Query Conditions:", where_clause)
    print("BOM Cost Variance Query Values:", values)

    data = frappe.db.sql(f"""
        SELECT
            se_item.item_code,
            se_item.item_name,
            se_item.qty,
            se_item.basic_rate AS actual_rate,
            bom_item.rate AS bom_rate,
            (se_item.basic_rate - bom_item.rate) AS variance,
            ((se_item.basic_rate - bom_item.rate)/bom_item.rate*100) AS variance_percent
        FROM `tabStock Entry` se
        INNER JOIN `tabStock Entry Detail` se_item
            ON se_item.parent = se.name
        INNER JOIN `tabBOM Item` bom_item
            ON bom_item.item_code = se_item.item_code
        WHERE {where_clause}
        ORDER BY variance DESC
        LIMIT 50
    """, values, as_dict=True)

    for d in data:
        d.qty = flt(d.qty, 2)
        d.actual_rate = flt(d.actual_rate, 2)
        d.bom_rate = flt(d.bom_rate, 2)
        d.variance = flt(d.variance, 2)
        d.variance_percent = flt(d.variance_percent, 2)

    return data
