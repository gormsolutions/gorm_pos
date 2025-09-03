import frappe
@frappe.whitelist()
def fetch_all_suppliers():
    suppliers = frappe.get_all(
        "Supplier",
        fields=["name"]
    )
    for supplier in suppliers:
        print(supplier)
    return suppliers


import frappe

@frappe.whitelist()
def fetch_material_transfers(from_date=None, to_date=None):
    current_user = frappe.session.user  # Logged-in user

    conditions = """
        se.docstatus = 1
        AND se.purpose = 'Material Transfer'
        AND sed.t_warehouse = 'Damaged Stores - AEL'
        AND se.owner = %s
    """
    params = [current_user]

    # Add date filters if provided
    if from_date and to_date:
        conditions += " AND se.posting_date BETWEEN %s AND %s"
        params.extend([from_date, to_date])
    elif from_date:
        conditions += " AND se.posting_date >= %s"
        params.append(from_date)
    elif to_date:
        conditions += " AND se.posting_date <= %s"
        params.append(to_date)

    stock_entries = frappe.db.sql(f"""
        SELECT 
            se.name AS stock_entry,
            se.owner,
            se.purpose,
            se.posting_date,
            se.posting_time,
            se.custom_customer,
            sed.item_code,
            sed.qty,
            sed.t_warehouse
        FROM 
            `tabStock Entry` se
        JOIN 
            `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE {conditions}
        ORDER BY se.posting_date DESC, se.posting_time DESC
    """, params, as_dict=True)

    return stock_entries
