import frappe

@frappe.whitelist()
def get_work_order_status_overview(from_date, to_date, company=None, cost_center=None, item_group=None):
    """
    Fetch Work Order Status Overview between given dates, excluding Cancelled Work Orders.
    
    Filters:
        - from_date, to_date (mandatory)
        - company (optional)
        - cost_center (optional)
        - item_group (optional)
    
    Returns:
        List of dicts with Work Order and Work Order Item details
    """
    
    # Base conditions
    conditions = [
        "wo.docstatus = 1",
        "wo.planned_start_date BETWEEN %(from_date)s AND %(to_date)s",
        "wi.include_item_in_manufacturing = 1",
        "wo.status != 'Cancelled'"  # Exclude cancelled Work Orders
    ]
    
    values = {
        "from_date": from_date,
        "to_date": to_date
    }

    if company:
        conditions.append("wo.company = %(company)s")
        values["company"] = company
    if cost_center:
        conditions.append("wo.cost_center = %(cost_center)s")
        values["cost_center"] = cost_center
    if item_group:
        conditions.append("i.item_group = %(item_group)s")
        values["item_group"] = item_group

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            wo.name AS work_order,
            wo.production_item,
            wo.item_name AS fg_name,
            wo.bom_no,
            wo.status,
            wo.planned_start_date,
            wo.actual_start_date,
            wo.actual_end_date,
            wi.item_code,
            wi.item_name,
            wi.required_qty,
            wi.transferred_qty AS produced_qty,
            wi.stock_uom,
            i.item_group
        FROM `tabWork Order` wo
        INNER JOIN `tabWork Order Item` wi ON wi.parent = wo.name
        LEFT JOIN `tabItem` i ON i.item_code = wi.item_code
        WHERE {where_clause}
        ORDER BY wo.planned_start_date DESC, wo.name, wi.idx
    """

    data = frappe.db.sql(query, values, as_dict=True)
    
    # Ensure numeric fields are floats
    for row in data:
        row["required_qty"] = float(row["required_qty"] or 0)
        row["produced_qty"] = float(row["produced_qty"] or 0)
    
    return data
