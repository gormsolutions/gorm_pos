import frappe

import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_items_sold(from_date, to_date, cost_center=None, company=None, warehouse=None,
                   item=None, item_group=None, mode_of_payment=None,
                   sales_invoice=None, start=0, page_length=50):
    """
    Fetch paginated items sold with optional filters including mode of payment and Sales Invoice No.
    """
    # --- Base conditions ---
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
        conditions.append("si.cost_center = %(cost_center)s")
        params["cost_center"] = cost_center
    if mode_of_payment:
        conditions.append("sip.mode_of_payment = %(mode_of_payment)s")
        params["mode_of_payment"] = mode_of_payment
    if sales_invoice:
        conditions.append("si.name = %(sales_invoice)s")
        params["sales_invoice"] = sales_invoice

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            sii.item_code,
            i.item_group,
            sii.qty,
            sii.rate,
            sii.amount,
            sii.warehouse,
            si.posting_date,
            si.cost_center,
            si.name AS sales_invoice,
            GROUP_CONCAT(DISTINCT sip.mode_of_payment) AS mode_of_payment
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        LEFT JOIN `tabItem` i ON i.name = sii.item_code
        LEFT JOIN `tabSales Invoice Payment` sip ON sip.parent = si.name
        WHERE {where_clause}
        GROUP BY sii.name, sii.idx
        ORDER BY si.posting_date DESC
        LIMIT %(start)s, %(page_length)s
    """

    data = frappe.db.sql(query, {**params, "start": int(start), "page_length": int(page_length)}, as_dict=True)

    for d in data:
        d['qty'] = flt(d.get('qty', 0))
        d['rate'] = flt(d.get('rate', 0))
        d['amount'] = flt(d.get('amount', 0))

    return data


import frappe

@frappe.whitelist()
def get_item_wise_sales_history(from_date, to_date, company=None, warehouse=None,
                                item=None, item_group=None, cost_center=None,
                                customer=None, sales_invoice=None,
                                start=0, page_length=50):
    """
    Fetch paginated item-wise sales history with optional filters,
    including sales invoice filter.
    """
    conditions = [
        "si.docstatus = 1",
        "si.posting_date BETWEEN %(from_date)s AND %(to_date)s"
    ]
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
        conditions.append("si.cost_center = %(cost_center)s")
        params["cost_center"] = cost_center
    if customer:
        conditions.append("si.customer = %(customer)s")
        params["customer"] = customer
    if sales_invoice:
        conditions.append("si.name = %(sales_invoice)s")
        params["sales_invoice"] = sales_invoice

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            sii.item_code,
            sii.item_name,
            i.item_group,
            SUM(sii.qty) as qty,
            AVG(sii.rate) as rate,
            SUM(sii.amount) as amount,
            sii.warehouse,
            si.cost_center,
            si.posting_date,
            si.customer,
            si.name as sales_invoice
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        LEFT JOIN `tabItem` i ON i.name = sii.item_code
        WHERE {where_clause}
        GROUP BY sii.item_code, sii.item_name, i.item_group,
                 sii.warehouse, si.cost_center, si.posting_date,
                 si.customer, si.name
        ORDER BY si.posting_date DESC
        LIMIT %(start)s, %(page_length)s
    """

    data = frappe.db.sql(
        query,
        {**params, "start": int(start), "page_length": int(page_length)},
        as_dict=True
    )
    return data
