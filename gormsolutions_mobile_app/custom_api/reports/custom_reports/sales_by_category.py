import frappe
from frappe.utils import getdate

@frappe.whitelist()
def get_sales_by_item_group(from_date=None, to_date=None, company=None, cost_center=None, item_group=None, download=0, limit_start=0, page_length=50):
    """
    Fetch sales invoice items grouped by Item Group and SKU,
    filtered by date range, company, cost center, optionally item group.
    Supports pagination.
    """
    from_date = getdate(from_date) if from_date else None
    to_date = getdate(to_date) if to_date else None
    download = int(download or 0)
    limit_start = int(limit_start or 0)
    page_length = int(page_length or 50)

    query = """
        SELECT
            i.item_group,
            sii.item_code,
            i.item_name,
            sii.cost_center,
            SUM(sii.qty) AS total_qty,
            SUM(sii.base_net_amount) AS total_amount
        FROM `tabSales Invoice Item` sii
        JOIN `tabItem` i ON i.name = sii.item_code
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.docstatus = 1
    """

    args = []

    if from_date:
        query += " AND si.posting_date >= %s"
        args.append(from_date)
    if to_date:
        query += " AND si.posting_date <= %s"
        args.append(to_date)
    if company:
        query += " AND si.company = %s"
        args.append(company)
    if cost_center:
        query += " AND sii.cost_center = %s"
        args.append(cost_center)
    if item_group:
        item_groups = [x.strip() for x in item_group.split(',')]
        placeholders = ', '.join(['%s'] * len(item_groups))
        query += f" AND i.item_group IN ({placeholders})"
        args.extend(item_groups)

    query += " GROUP BY i.item_group, sii.item_code, i.item_name, sii.cost_center"
    query += " ORDER BY i.item_group, sii.item_code"
    query += " LIMIT %s OFFSET %s"
    args.extend([page_length, limit_start])

    return frappe.db.sql(query, tuple(args), as_dict=True)
