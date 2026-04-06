import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_gross_profit_margin(company, from_date, to_date, cost_center=None):

    filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date
    }

    cost_center_condition = ""
    if cost_center:
        cost_center_condition = "AND gle.cost_center = %(cost_center)s"
        filters["cost_center"] = cost_center

    data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,

            SUM(
                IF(acc.root_type = 'Income',
                    gle.credit - gle.debit,
                    0)
            ) AS revenue,

            SUM(
                IF(acc.account_type = 'Cost of Goods Sold',
                    gle.debit - gle.credit,
                    0)
            ) AS cogs

        FROM `tabGL Entry` gle

        INNER JOIN (
            SELECT name, root_type, account_type
            FROM `tabAccount`
            WHERE root_type = 'Income'
               OR account_type = 'Cost of Goods Sold'
        ) acc ON acc.name = gle.account

        WHERE
            gle.company = %(company)s
            AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND gle.is_cancelled = 0
            {cost_center_condition}

        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    result = []

    for row in data:
        revenue = flt(row.revenue)
        cogs = flt(row.cogs)
        gross_profit = revenue - cogs
        margin = (gross_profit / revenue * 100) if revenue else 0

        result.append({
            "cost_center": row.cost_center,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "gross_profit_margin_percent": round(margin, 2)
        })

    return result