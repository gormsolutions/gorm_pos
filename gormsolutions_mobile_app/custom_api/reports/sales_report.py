import frappe
from datetime import datetime
from collections import defaultdict

@frappe.whitelist()
def fetch_sales_by_date_range(start_date, end_date):
    """
    Fetch sales invoices from Frappe ERPNext within a date range, including all items, 
    and calculate total sales, total paid, and total credit per owner, including their full names.
    Push updates in real-time using WebSockets.
    :param start_date: Start date of the range (YYYY-MM-DD)
    :param end_date: End date of the range (YYYY-MM-DD)
    """
    try:
        # Validate date inputs
        if not start_date or not end_date:
            return {"error": "Start date and end date are required."}

        # Query Sales Invoices with filters
        sales_invoices = frappe.get_all(
            "Sales Invoice",
            filters={
                "posting_date": ["between", [start_date, end_date]],
                "docstatus": 1  # Only submitted invoices
            },
            fields=["name", "customer", "grand_total", "outstanding_amount", "posting_date", "owner"]
        )

        # Fetch items for each invoice and group by owner
        grouped_sales = defaultdict(lambda: {"invoices": [], "total_sales": 0, "total_paid": 0, "total_credit": 0, "full_name": ""})
        for invoice in sales_invoices:
            # Fetch items for the current invoice
            items = frappe.get_all(
                "Sales Invoice Item",
                filters={"parent": invoice["name"]},
                fields=["item_code", "item_name", "qty", "rate", "amount","uom"]
            )
            invoice["items"] = items  # Add items to the invoice

            # Calculate paid and credit amounts
            paid_amount = invoice["grand_total"] - invoice["outstanding_amount"]
            credit_amount = invoice["outstanding_amount"]

            # Fetch the full name of the owner
            if not grouped_sales[invoice["owner"]]["full_name"]:
                user = frappe.get_value("User", invoice["owner"], "full_name")
                grouped_sales[invoice["owner"]]["full_name"] = user or invoice["owner"]

            # Group by owner and calculate totals
            grouped_sales[invoice["owner"]]["invoices"].append(invoice)
            grouped_sales[invoice["owner"]]["total_sales"] += invoice["grand_total"]
            grouped_sales[invoice["owner"]]["total_paid"] += paid_amount
            grouped_sales[invoice["owner"]]["total_credit"] += credit_amount

        # Publish real-time updates using WebSockets
        frappe.publish_realtime(
            event="sales_data_update",
            message={"grouped_sales": grouped_sales},
            user=frappe.session.user  # Send updates to the current user
        )

        return grouped_sales

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Fetch Sales by Date Range Error")
        return {"error": str(e)}