import frappe

@frappe.whitelist()
def get_sales_register(from_date, to_date, company=None, customer=None, department=None,
                       invoice=None, mode_of_payment=None, cost_center=None, warehouse=None,
                       owner=None, item_group=None, customer_group=None,
                       start=0, page_length=50):
    """
    Optimized Sales Register query with extended filters and pagination.
    """

    conditions = ["si.docstatus = 1", "si.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
    params = {"from_date": from_date, "to_date": to_date}

    if company:
        conditions.append("si.company = %(company)s")
        params["company"] = company
    if customer:
        conditions.append("si.customer = %(customer)s")
        params["customer"] = customer
    if department:
        conditions.append("si.department = %(department)s")
        params["department"] = department
    if invoice:
        conditions.append("si.name = %(invoice)s")
        params["invoice"] = invoice
    if mode_of_payment:
        conditions.append("mp.mode_of_payment = %(mode_of_payment)s")
        params["mode_of_payment"] = mode_of_payment
    if cost_center:
        conditions.append("sii.cost_center = %(cost_center)s")
        params["cost_center"] = cost_center
    if warehouse:
        conditions.append("sii.warehouse = %(warehouse)s")
        params["warehouse"] = warehouse
    if owner:
        conditions.append("si.owner = %(owner)s")
        params["owner"] = owner
    if item_group:
        conditions.append("i.item_group = %(item_group)s")
        params["item_group"] = item_group
    if customer_group:
        conditions.append("si.customer_group = %(customer_group)s")
        params["customer_group"] = customer_group

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            si.name as invoice,
            si.customer,
            si.customer_group,
            mp.mode_of_payment,
            si.grand_total,
            si.paid_amount,
            si.outstanding_amount,
            si.posting_date,
            si.owner,
            sii.cost_center,
            sii.warehouse,
            i.item_group
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Invoice Payment` mp ON mp.parent = si.name
        LEFT JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        LEFT JOIN `tabItem` i ON i.name = sii.item_code
        WHERE {where_clause}
        ORDER BY si.posting_date DESC, si.name DESC
        LIMIT %(start)s, %(page_length)s
    """

    data = frappe.db.sql(query, {**params, "start": int(start), "page_length": int(page_length)}, as_dict=True)
    return data
