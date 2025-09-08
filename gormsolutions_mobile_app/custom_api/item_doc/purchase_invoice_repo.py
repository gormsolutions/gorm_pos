import frappe
from collections import defaultdict

@frappe.whitelist()
def get_purchase_invoices_for_supplier(supplier_name=None):
    # Set base filters: submitted invoices from May 1st, 2025
    filters = {
        "docstatus": 1,
        "posting_date": [">=", "2025-05-01"]
    }

    # Optionally filter by supplier
    if supplier_name:
        filters["supplier"] = supplier_name

    # Fetch invoices
    purchase_invoices = frappe.get_all(
        "Purchase Invoice",
        filters=filters,
        fields=["name", "supplier", "status", "grand_total", "posting_date","outstanding_amount"]
    )

    # Grouped results by supplier
    grouped_results = defaultdict(lambda: {
        "invoices": [],
        "total_grand_total": 0.0,
        "total_outstanding": 0.0
    })

    for invoice in purchase_invoices:
        # Fetch items for each invoice
        items = frappe.get_all(
            "Purchase Invoice Item",
            filters={"parent": invoice["name"]},
            fields=["item_name", "uom", "qty", "rate", "amount","stock_qty",]
        )

        supplier = invoice["supplier"]
        grouped_results[supplier]["invoices"].append({
            "invoice_name": invoice["name"],
            "status": invoice["status"],
            "posting_date": invoice["posting_date"],
            "grand_total": invoice["grand_total"],
            "outstanding_amount": invoice["outstanding_amount"],
            "items": items
        })

        grouped_results[supplier]["total_grand_total"] += invoice["grand_total"]
        grouped_results[supplier]["total_outstanding"] += invoice["outstanding_amount"]

    # Return specific supplier data if requested
    if supplier_name:
        return {
            "supplier": supplier_name,
            **grouped_results.get(supplier_name, {
                "invoices": [],
                "total_grand_total": 0.0,
                "total_outstanding": 0.0
            })
        }

    # Otherwise return grouped data for all suppliers
    return grouped_results
