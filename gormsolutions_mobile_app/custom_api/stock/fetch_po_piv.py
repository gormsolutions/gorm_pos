import frappe

@frappe.whitelist()
def fetch_purchase_orders_and_invoices():
    """
    Fetch all Purchase Orders and Purchase Invoices with their items, grouped by document name, excluding canceled documents.
    Exclude Purchase Invoices with an outstanding amount of zero and items with the name 'Opening Invoice Item'.
    Include the purchase_order field in Purchase Invoice items.
    :return: A dictionary containing grouped Purchase Orders and Purchase Invoices with their items.
    """
    try:
        # Fetch all Purchase Orders excluding canceled ones
        purchase_orders_raw = frappe.db.sql("""
            SELECT 
                po.name AS purchase_order,
                po.supplier,
                po.status,
                po.transaction_date,
                poi.item_code,
                poi.item_name,
                poi.qty,
                poi.rate,
                poi.amount
            FROM 
                `tabPurchase Order` po
            INNER JOIN 
                `tabPurchase Order Item` poi ON po.name = poi.parent
            WHERE 
                po.docstatus != 2
        """, as_dict=True)

        # Group Purchase Orders by name
        purchase_orders = {}
        for row in purchase_orders_raw:
            if row["purchase_order"] not in purchase_orders:
                purchase_orders[row["purchase_order"]] = {
                    "supplier": row["supplier"],
                    "status": row["status"],
                    "transaction_date": row["transaction_date"],
                    "items": []
                }
            purchase_orders[row["purchase_order"]]["items"].append({
                "item_code": row["item_code"],
                "item_name": row["item_name"],
                "qty": row["qty"],
                "rate": row["rate"],
                "amount": row["amount"]
            })

        # Fetch all Purchase Invoices excluding canceled ones, with outstanding amount > 0, and excluding 'Opening Invoice Item'
        purchase_invoices_raw = frappe.db.sql("""
            SELECT 
                pi.name AS purchase_invoice,
                pi.supplier,
                pi.status,
                pi.outstanding_amount,
                pi.posting_date,
                pii.item_code,
                pii.item_name,
                pii.qty,
                pii.rate,
                pii.purchase_order,
                pii.amount
            FROM 
                `tabPurchase Invoice` pi
            INNER JOIN 
                `tabPurchase Invoice Item` pii ON pi.name = pii.parent
            WHERE 
                pi.docstatus != 2 
                AND pi.outstanding_amount > 0
                AND pii.item_name != 'Opening Invoice Item'
        """, as_dict=True)

        # Group Purchase Invoices by name
        purchase_invoices = {}
        for row in purchase_invoices_raw:
            if row["purchase_invoice"] not in purchase_invoices:
                purchase_invoices[row["purchase_invoice"]] = {
                    "supplier": row["supplier"],
                    "status": row["status"],
                    "outstanding_amount": row["outstanding_amount"],
                    "posting_date": row["posting_date"],
                    "items": []
                }
            purchase_invoices[row["purchase_invoice"]]["items"].append({
                "item_code": row["item_code"],
                "item_name": row["item_name"],
                "qty": row["qty"],
                "rate": row["rate"],
                "amount": row["amount"],
                "purchase_order": row["purchase_order"]  # Include the purchase_order field
            })

        return {
            "status": "success",
            "purchase_orders": purchase_orders,
            "purchase_invoices": purchase_invoices
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error fetching Purchase Orders and Invoices")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }