import frappe

@frappe.whitelist()
def get_sales_report_optimized(start_date, end_date, company=None, cost_center=None,
                               sales_invoice_no=None, item_code=None, flavour=None, start=0, page_length=50):
    filters = {"start_date": start_date, "end_date": end_date}
    conditions = ["si.posting_date BETWEEN %(start_date)s AND %(end_date)s"]

    if company:
        conditions.append("si.company = %(company)s")
        filters["company"] = company
    if cost_center:
        conditions.append("sii.cost_center = %(cost_center)s")
        filters["cost_center"] = cost_center
    if sales_invoice_no:
        conditions.append("si.name = %(sales_invoice_no)s")
        filters["sales_invoice_no"] = sales_invoice_no
    if item_code:
        conditions.append("sii.item_code = %(item_code)s")
        filters["item_code"] = item_code
    if flavour:
        conditions.append("iva.attribute='FLAVOUR' AND iva.attribute_value = %(flavour)s")
        filters["flavour"] = flavour

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            sii.item_code,
            SUM(sii.qty) AS qty_sold,
            SUM(sii.amount) AS amount,
            MAX(CASE WHEN iva.attribute='SIZE' THEN iva.attribute_value END) AS size,
            MAX(CASE WHEN iva.attribute='FLAVOUR' THEN iva.attribute_value END) AS flavour,
            si.company,
            sii.cost_center,
            si.name AS sales_invoice_no
        FROM `tabSales Invoice Item` AS sii
        JOIN `tabSales Invoice` AS si
            ON si.name = sii.parent
        LEFT JOIN `tabItem Variant Attribute` AS iva
            ON iva.parent = sii.item_code
            AND iva.attribute IN ('SIZE', 'FLAVOUR')
        WHERE {where_clause}
        GROUP BY sii.item_code, si.company, sii.cost_center, si.name
        ORDER BY sii.item_code
        LIMIT {page_length} OFFSET {start}
    """

    return frappe.db.sql(query, filters, as_dict=True)
