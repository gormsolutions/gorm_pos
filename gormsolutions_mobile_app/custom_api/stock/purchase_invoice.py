import frappe
from frappe import _

@frappe.whitelist()
def get_purchase_invoices_grouped_by_supplier(from_date=None, to_date=None, company="Shell Elgon"):
    """
    Fetch submitted Purchase Invoices grouped by supplier,
    only for cost centers under parent 'Hashim Gas Limited - SE',
    not disabled, and restricted to user-permitted cost centers.
    Includes invoice items.
    """

    current_user = frappe.session.user
    parent_cost_center = "Hashim Gas Limited - SE"

    # Get user-permitted Cost Centers from User Permission
    user_permissions = frappe.get_all(
        'User Permission',
        filters={
            'user': current_user,
            'allow': 'Cost Center',
        },
        fields=['for_value']
    )
    permitted_cost_centers = [d['for_value'] for d in user_permissions]

    if not permitted_cost_centers:
        # No permissions, return empty
        return []

    # Ensure only cost centers under the parent and not disabled
    child_cost_centers = frappe.db.sql_list("""
        SELECT name FROM `tabCost Center`
        WHERE parent_cost_center = %s
          AND disabled = 0
          AND name IN %s
    """, (parent_cost_center, tuple(permitted_cost_centers)))

    if not child_cost_centers:
        return []

    # Build filters
    conditions = ["pi.docstatus = 1"]
    filters = {"cost_centers": tuple(child_cost_centers)}

    if from_date:
        conditions.append("pi.posting_date >= %(from_date)s")
        filters["from_date"] = from_date

    if to_date:
        conditions.append("pi.posting_date <= %(to_date)s")
        filters["to_date"] = to_date

    if company:
        conditions.append("pi.company = %(company)s")
        filters["company"] = company

    conditions.append("pi.cost_center IN %(cost_centers)s")

    # Fetch invoices
    query = f"""
        SELECT
            pi.name AS invoice_no,
            pi.supplier,
            pi.supplier_name,
            pi.posting_date,
            pi.posting_time,
            pi.status,
            pi.base_grand_total AS total_amount,
            pi.currency,
            pi.company,
            pi.cost_center
        FROM `tabPurchase Invoice` pi
        WHERE {" AND ".join(conditions)}
        ORDER BY pi.supplier, pi.posting_date DESC
    """

    invoices = frappe.db.sql(query, filters, as_dict=True)

    # Fetch items for all invoices at once
    invoice_names = [inv["invoice_no"] for inv in invoices]
    items = {}
    if invoice_names:
        item_rows = frappe.db.sql("""
            SELECT parent AS invoice_no, item_code, item_name, qty, uom, rate, amount
            FROM `tabPurchase Invoice Item`
            WHERE parent IN %s
        """, (tuple(invoice_names),), as_dict=True)

        for row in item_rows:
            inv_no = row["invoice_no"]
            if inv_no not in items:
                items[inv_no] = []
            items[inv_no].append(row)

    # Group by supplier
    grouped = {}
    for inv in invoices:
        supplier = inv["supplier"]
        if supplier not in grouped:
            grouped[supplier] = {
                "supplier_name": inv["supplier_name"],
                "invoices": [],
                "total_amount": 0
            }

        # Add items to invoice
        inv["items"] = items.get(inv["invoice_no"], [])
        grouped[supplier]["invoices"].append(inv)
        grouped[supplier]["total_amount"] += inv["total_amount"]

    # Convert to list
    result = []
    for supplier, data in grouped.items():
        result.append({
            "supplier": supplier,
            "supplier_name": data["supplier_name"],
            "total_amount": data["total_amount"],
            "invoices": data["invoices"]
        })

    return result
