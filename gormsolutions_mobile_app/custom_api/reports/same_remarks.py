import frappe

@frappe.whitelist()
def get_gormpos_invoices_with_same_remarks(remarks=None, from_date=None, to_date=None, cost_center=None):
    """
    Fetch submitted, non-return GormPos invoices.
    - Optional filter by remarks
    - Optional filter by posting date between from_date and to_date
    - Optional filter by cost_center
    - If no remarks → return invoices with duplicate remarks only
    - Also returns count per Cost Center (high to low)
    """

    conditions = """
        si.docstatus = 1
        AND si.is_return = 0
        AND si.custom_from = 'GormPos'
    """

    params = {}

    # Optional filters
    if remarks:
        conditions += " AND si.remarks = %(remarks)s"
        params["remarks"] = remarks
    if from_date:
        conditions += " AND si.posting_date >= %(from_date)s"
        params["from_date"] = from_date
    if to_date:
        conditions += " AND si.posting_date <= %(to_date)s"
        params["to_date"] = to_date
    if cost_center:
        conditions += " AND si.cost_center = %(cost_center)s"
        params["cost_center"] = cost_center

    # ---------- INVOICE QUERY ----------
    if remarks:
        invoices_query = f"""
            SELECT
                si.name,
                si.remarks,
                si.cost_center,
                si.posting_date,
                si.posting_time,
                si.owner
            FROM `tabSales Invoice` si
            WHERE {conditions}
            ORDER BY si.posting_date DESC, si.posting_time DESC
        """

        cost_center_query = f"""
            SELECT
                si.cost_center,
                COUNT(*) AS total
            FROM `tabSales Invoice` si
            WHERE {conditions}
            GROUP BY si.cost_center
            ORDER BY total DESC
        """
    else:
        invoices_query = f"""
            WITH duplicate_remarks AS (
                SELECT remarks
                FROM `tabSales Invoice`
                WHERE
                    docstatus = 1
                    AND is_return = 0
                    AND custom_from = 'GormPos'
                    AND remarks IS NOT NULL
                    AND remarks != ''
                GROUP BY remarks
                HAVING COUNT(*) > 1
            )
            SELECT
                si.name,
                si.remarks,
                si.cost_center,
                si.posting_date,
                si.posting_time,
                si.owner
            FROM `tabSales Invoice` si
            JOIN duplicate_remarks dr ON dr.remarks = si.remarks
            WHERE {conditions}
            ORDER BY si.posting_date DESC, si.posting_time DESC
        """

        cost_center_query = f"""
            WITH duplicate_remarks AS (
                SELECT remarks
                FROM `tabSales Invoice`
                WHERE
                    docstatus = 1
                    AND is_return = 0
                    AND custom_from = 'GormPos'
                    AND remarks IS NOT NULL
                    AND remarks != ''
                GROUP BY remarks
                HAVING COUNT(*) > 1
            )
            SELECT
                si.cost_center,
                COUNT(*) AS total
            FROM `tabSales Invoice` si
            JOIN duplicate_remarks dr ON dr.remarks = si.remarks
            WHERE {conditions}
            GROUP BY si.cost_center
            ORDER BY total DESC
        """

    invoices = frappe.db.sql(invoices_query, params, as_dict=True)
    cost_center_counts = frappe.db.sql(cost_center_query, params, as_dict=True)

    return {
        "invoices": invoices,
        "cost_center_counts": cost_center_counts
    }
