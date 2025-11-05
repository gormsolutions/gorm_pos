import frappe
from frappe.utils import getdate, flt

@frappe.whitelist()
def get_purchases_by_supplier(company=None, from_date=None, to_date=None, cost_center=None):
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # Prepare SQL filter
    filters = ["pi.docstatus = 1"]
    if company:
        filters.append(f"pi.company = '{company}'")
    if cost_center:
        filters.append(f"pi.cost_center = '{cost_center}'")
    where_clause = " AND ".join(filters)

    # Purchases grouped by supplier
    purchases = frappe.db.sql(f"""
        SELECT pi.supplier AS supplier,
               IFNULL(supplier.supplier_name, '') AS supplier_name,
               SUM(pi.grand_total) AS total_purchase
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabSupplier` supplier ON supplier.name = pi.supplier
        WHERE pi.posting_date BETWEEN '{from_date}' AND '{to_date}'
        AND {where_clause}
        GROUP BY pi.supplier
        HAVING SUM(pi.grand_total) > 0
        ORDER BY total_purchase DESC
    """, as_dict=1)

    return purchases
