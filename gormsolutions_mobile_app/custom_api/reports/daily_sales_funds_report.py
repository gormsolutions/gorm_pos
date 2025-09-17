import frappe

@frappe.whitelist()
def get_daily_sales_funds(from_date=None, to_date=None, company=None, cost_center=None, account=None, limit_start=0, limit_page_length=50):
    """
    Get Daily Sales Funds report.
    from_date, to_date are optional. If not provided, all dates are considered.
    """
    limit_start = int(limit_start or 0)
    limit_page_length = int(limit_page_length or 50)

    if not company:
        frappe.throw("Please provide a Company")

    conditions = ["gle.is_cancelled = 0", "acc.account_type = 'Bank'", "gle.voucher_type != 'Journal Entry'"]

    if from_date and to_date:
        conditions.append("gle.posting_date BETWEEN %(from_date)s AND %(to_date)s")
    if company:
        conditions.append("gle.company = %(company)s")
    if cost_center:
        conditions.append("gle.cost_center = %(cost_center)s")
    if account:
        conditions.append("gle.account = %(account)s")

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT 
            gle.account,
            SUM(gle.debit) AS inflows
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE {where_clause}
        GROUP BY gle.account
        ORDER BY inflows DESC
        LIMIT {limit_start}, {limit_page_length}
    """

    params = {
        "from_date": from_date,
        "to_date": to_date,
        "company": company,
        "cost_center": cost_center,
        "account": account
    }

    return frappe.db.sql(query, params, as_dict=True)
