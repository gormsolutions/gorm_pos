import frappe
from frappe.utils import getdate, flt

@frappe.whitelist()
def get_price_variance(supplier=None, item_code=None, company=None, cost_center=None, from_date=None, to_date=None):
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # Prepare filters
    filters = ["pi.docstatus = 1"]
    if company:
        filters.append(f"pi.company = '{company}'")
    if supplier:
        filters.append(f"pi.supplier = '{supplier}'")
    if item_code:
        filters.append(f"pid.item_code = '{item_code}'")
    if cost_center:
        filters.append(f"pi.cost_center = '{cost_center}'")

    where_clause = " AND ".join(filters)

    # Fetch purchase invoices with item rates
    purchases = frappe.db.sql(f"""
        SELECT pi.supplier,
               IFNULL(supplier.supplier_name,'') AS supplier_name,
               pid.item_code,
               IFNULL(item.item_name,'') AS item_name,
               pid.rate AS purchase_rate,
               pid.qty,
               pid.amount,
               COALESCE(item.standard_rate, pid.rate) AS standard_rate,
               pid.rate - COALESCE(item.standard_rate, pid.rate) AS variance
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pid ON pid.parent = pi.name
        LEFT JOIN `tabSupplier` supplier ON supplier.name = pi.supplier
        LEFT JOIN `tabItem` item ON item.name = pid.item_code
        WHERE pi.posting_date BETWEEN '{from_date}' AND '{to_date}'
        AND {where_clause}
        ORDER BY supplier, item_code
    """, as_dict=1)

    # Only return records with variance
    purchases = [p for p in purchases if flt(p['variance']) != 0]

    return purchases
