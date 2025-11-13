import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def create_sales_return(sales_invoice_name, items, return_date=None, remarks=None):
    """
    Create and submit a Sales Return (Credit Note) linked to a Sales Invoice.
    Allows partial item returns and new (non-invoice) items.

    Args:
        sales_invoice_name (str): Original Sales Invoice name (e.g. 'SINV-0001')
        items (list[dict]): Items to return, e.g.
            [{"item_code": "ITEM-001", "qty": 2, "rate": 150}]
        return_date (str, optional): Date of return (defaults to today)
        remarks (str, optional): Notes or reason for return

    Returns:
        dict: JSON response with Sales Return details
    """
    try:
        if not sales_invoice_name:
            frappe.throw("Sales Invoice name is required.")
        if not items:
            frappe.throw("Please specify at least one item to return.")

        # Parse JSON if items is a string
        if isinstance(items, str):
            import json
            items = json.loads(items)

        # Get original invoice
        original_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
        if not original_invoice:
            frappe.throw("Original Sales Invoice not found.")
        if original_invoice.docstatus != 1:
            frappe.throw("Only submitted Sales Invoices can be returned.")

        # Prepare new return invoice
        return_invoice = frappe.new_doc("Sales Invoice")
        return_invoice.is_return = 1
        return_invoice.return_against = original_invoice.name
        return_invoice.customer = original_invoice.customer
        return_invoice.company = original_invoice.company
        return_invoice.posting_date = return_date or nowdate()
        return_invoice.due_date = return_date or nowdate()
        return_invoice.remarks = remarks or f"Sales return for {original_invoice.name}"
        return_invoice.update_stock = original_invoice.update_stock

        # Extract default cost_center & warehouse from first original item
        default_cost_center = (
            original_invoice.items[0].cost_center if original_invoice.items else None
        )
        default_warehouse = (
            original_invoice.items[0].warehouse if original_invoice.items else None
        )

        # Add return items (mix of old & new allowed)
        for r_item in items:
            item_code = r_item.get("item_code")
            qty = abs(float(r_item.get("qty", 0)))
            rate = float(r_item.get("rate", 0))

            if not item_code or qty <= 0:
                continue

            # Try to get warehouse/cost_center from original invoice item
            inv_item = next(
                (i for i in original_invoice.items if i.item_code == item_code),
                None
            )

            return_invoice.append("items", {
                "item_code": item_code,
                "qty": -qty,  # Always negative
                "rate": rate or (inv_item.rate if inv_item else 0),
                "income_account": (inv_item.income_account if inv_item else None),
                "cost_center": (inv_item.cost_center if inv_item else default_cost_center),
                "warehouse": (inv_item.warehouse if inv_item else default_warehouse),
                "description": (
                    inv_item.description
                    if inv_item else frappe.db.get_value("Item", item_code, "description")
                ),
                "uom": (inv_item.uom if inv_item else frappe.db.get_value("Item", item_code, "stock_uom")),
            })

        if not return_invoice.items:
            frappe.throw("No valid items found to return.")

        # Save & submit
        return_invoice.insert(ignore_permissions=True)
        return_invoice.submit()
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Sales Return {return_invoice.name} created successfully.",
            "sales_return": return_invoice.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sales Return Creation Failed")
        frappe.throw(f"Sales Return creation failed: {str(e)}")
