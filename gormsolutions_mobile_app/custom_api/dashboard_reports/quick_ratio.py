import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_quick_ratio(company, cost_center=None):
    """
    Returns Quick Ratio per cost center.
    - company: Company name
    - cost_center: optional filter
    """

    filters = {"company": company}
    cost_center_condition = ""
    if cost_center:
        cost_center_condition = "AND gle.cost_center = %(cost_center)s"
        filters["cost_center"] = cost_center

    # 1️⃣ Liquid Assets: Cash + Bank + Accounts Receivable
    liquid_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,
            SUM(
                CASE
                    WHEN acc.account_type IN ('Cash', 'Bank', 'Receivable')
                    THEN gle.debit - gle.credit
                    ELSE 0
                END
            ) AS liquid_assets
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND gle.is_cancelled = 0
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    liquid_map = {row.cost_center if row.cost_center else "Unassigned": flt(row.liquid_assets) for row in liquid_data}

    # 2️⃣ Current Liabilities: Accounts Payable + Short-term Liabilities
    liabilities_data = frappe.db.sql(f"""
        SELECT
            gle.cost_center,
            SUM(
                CASE
                    WHEN acc.account_type IN ('Payable', 'Current Liability')
                    THEN gle.credit - gle.debit
                    ELSE 0
                END
            ) AS current_liabilities
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE
            gle.company = %(company)s
            AND gle.is_cancelled = 0
            {cost_center_condition}
        GROUP BY gle.cost_center
    """, filters, as_dict=True)

    liability_map = {row.cost_center if row.cost_center else "Unassigned": flt(row.current_liabilities) for row in liabilities_data}

    # ----------------------------
    # 3️⃣ Calculate Quick Ratio & Classification
    # ----------------------------
    all_ccs = set(list(liquid_map.keys()) + list(liability_map.keys()))
    result = []

    for cc in all_ccs:
        liquid = liquid_map.get(cc, 0)
        liabilities = liability_map.get(cc, 0)

        # Avoid division by zero
        quick_ratio = (liquid / liabilities) if liabilities > 0 else 0

        # Classification
        if quick_ratio >= 1:
            status = "Safe"
        elif 0.7 <= quick_ratio < 1:
            status = "Moderate Risk"
        else:
            status = "High Risk"

        result.append({
            "cost_center": cc,
            "liquid_assets": round(liquid, 2),
            "current_liabilities": round(liabilities, 2),
            "quick_ratio": round(quick_ratio, 2),
            "status": status
        })

    return result