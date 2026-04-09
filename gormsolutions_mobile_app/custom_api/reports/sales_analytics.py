import frappe

@frappe.whitelist()
def get_sales_analytics(from_date=None, to_date=None, company=None, customer=None,
                        limit_start=0, limit_page_length=50, based_on="Sales Invoice", value_or_qty="Value", range="Monthly"):
    """
    Fetch Sales Analytics:
    - Filtered by date range, company, customer
    - Supports pagination via limit_start and limit_page_length
    """
    conditions = ["si.docstatus = 1"]
    params = {}

    # --- Date filter ---
    if from_date and to_date:
        conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")
        params.update({"from_date": from_date, "to_date": to_date})

    # --- Extra filters ---
    if company:
        conditions.append("si.company = %(company)s")
        params["company"] = company
    if customer:
        conditions.append("si.customer = %(customer)s")
        params["customer"] = customer

    where_clause = " AND ".join(conditions)

    # --- SQL Query with Pagination ---
    query = f"""
        SELECT 
            si.customer,
            si.customer_name,
            MONTHNAME(si.posting_date) AS month,
            SUM(si.grand_total) AS total
        FROM `tabSales Invoice` si
        WHERE {where_clause}
        GROUP BY si.customer, si.customer_name, MONTH(si.posting_date)
        ORDER BY si.customer_name
        LIMIT {limit_start}, {limit_page_length}
    """
    data = frappe.db.sql(query, params, as_dict=True)

    # --- Pivot into customer rows with monthly + total columns ---
    results = {}
    for row in data:
        cust = row.customer
        if cust not in results:
            results[cust] = {
                "customer": cust,
                "customer_name": row.customer_name,
                "months": {},
                "total": 0
            }
        results[cust]["months"][row.month] = row.total
        results[cust]["total"] += row.total

    return list(results.values())
