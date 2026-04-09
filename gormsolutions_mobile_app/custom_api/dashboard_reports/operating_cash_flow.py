import frappe
from frappe.utils import flt, nowdate, add_months

@frappe.whitelist()
def get_operating_cash_flow(company, from_date=None, to_date=None, cost_center=None):
    """
    Returns Operating Cash Flow per cost center.
    - from_date, to_date: optional filter; defaults to current month if not provided
    - cost_center: optional filter
    """

    # Default dates
    if not to_date:
        to_date = nowdate()
    if not from_date:
        from_date = add_months(to_date, -1)  # last month

    filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date
    }

    cost_center_condition = ""
    if cost_center:
        cost_center_condition = "AND gle.cost_center = %(cost_center)s"
        filters["cost_center"] = cost_center

    # ----------------------------
    # 1️⃣ Aggregate Cash Flow by Cost Center
    # ----------------------------
    ocf_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,

            SUM(
                IF(acc.root_type = 'Income', gle.credit - gle.debit, 0)
            ) AS cash_inflows,

            SUM(
                IF(acc.root_type = 'Expense', gle.debit - gle.credit, 0)
            ) AS cash_outflows

        FROM `tabGL Entry` gle
        INNER JOIN (
            SELECT name, root_type
            FROM `tabAccount`
            WHERE root_type IN ('Income', 'Expense')
        ) acc ON acc.name = gle.account

        WHERE
            gle.company = %(company)s
            AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND gle.is_cancelled = 0
            {cost_center_condition}

        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    result = []
    for row in ocf_data:
        inflows = flt(row.cash_inflows)
        outflows = flt(row.cash_outflows)
        net_ocf = inflows - outflows

        # Optional risk classification
        if net_ocf < 0:
            status = "Negative OCF"
        elif net_ocf == 0:
            status = "Neutral OCF"
        else:
            status = "Positive OCF"

        result.append({
            "cost_center": row.cost_center,
            "cash_inflows": round(inflows, 2),
            "cash_outflows": round(outflows, 2),
            "net_operating_cash_flow": round(net_ocf, 2),
            "status": status
        })

    return result