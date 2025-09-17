import frappe
from frappe import _

@frappe.whitelist()
def get_item_wise_sales_register(from_date, to_date, company=None, warehouse=None,
                                 item=None, item_group=None, cost_center=None,
                                 customer=None, invoice=None, start=0, page_length=50):
    """
    Optimized Item-wise Sales Register (ERPNext v15 compatible)
    with pagination and filters, including invoice filter.
    """
    conditions = ["si.docstatus = 1", "si.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
    params = {"from_date": from_date, "to_date": to_date}

    if company:
        conditions.append("si.company = %(company)s")
        params["company"] = company
    if warehouse:
        conditions.append("sii.warehouse = %(warehouse)s")
        params["warehouse"] = warehouse
    if item:
        conditions.append("sii.item_code = %(item)s")
        params["item"] = item
    if item_group:
        conditions.append("i.item_group = %(item_group)s")
        params["item_group"] = item_group
    if cost_center:
        conditions.append("sii.cost_center = %(cost_center)s")
        params["cost_center"] = cost_center
    if customer:
        conditions.append("si.customer = %(customer)s")
        params["customer"] = customer
    if invoice:
        # Support for single invoice or list of invoices
        if isinstance(invoice, str):
            conditions.append("si.name = %(invoice)s")
            params["invoice"] = invoice
        elif isinstance(invoice, list) and invoice:
            invoice_list = ", ".join(["%({0})s".format(i) for i in range(len(invoice))])
            conditions.append(f"si.name IN ({invoice_list})")
            for idx, inv in enumerate(invoice):
                params[str(idx)] = inv

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            sii.item_code,
            sii.item_name,
            i.item_group,
            sii.description,
            si.name AS invoice,
            si.posting_date,
            si.customer_group,
            si.customer,
            si.customer_name,
            si.debit_to AS receivable_account,
            si.company,
            si.project,
            si.territory,
            sii.sales_order,
            sii.delivery_note,
            sii.income_account,
            sii.cost_center,
            sii.stock_qty,
            sii.stock_uom,
            sii.rate,
            sii.amount,
            sii.base_amount,
            sii.net_rate,
            sii.net_amount,
            sii.base_net_amount,
            si.total_taxes_and_charges AS total_tax,
            si.discount_amount AS total_discount,
            (si.total_taxes_and_charges - IFNULL(si.discount_amount,0)) AS total_other_charges,
            (SELECT mop.mode_of_payment
             FROM `tabSales Invoice Payment` mop
             WHERE mop.parent = si.name
             LIMIT 1) AS mode_of_payment
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        LEFT JOIN `tabItem` i ON i.name = sii.item_code
        WHERE {where_clause}
        ORDER BY si.posting_date DESC, si.posting_time DESC, si.name DESC
        LIMIT %(start)s, %(page_length)s
    """

    data = frappe.db.sql(
        query,
        {**params, "start": int(start), "page_length": int(page_length)},
        as_dict=True
    )
    return data
