import frappe
from datetime import datetime
from collections import defaultdict

@frappe.whitelist()
def fetch_daily_sales():
    """
    Fetch daily sales invoices from Frappe ERPNext and group them by owner.
    """
    try:
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')

        # Query Sales Invoices with filters
        sales_invoices = frappe.get_all(
            "Sales Invoice",
            filters={
                "posting_date": today,
                "docstatus": 1  # Only submitted invoices
            },
            fields=["name", "customer", "grand_total", "posting_date", "owner"]
        )

        # Group sales invoices by owner
        grouped_sales = defaultdict(list)
        for invoice in sales_invoices:
            grouped_sales[invoice["owner"]].append(invoice)

        return grouped_sales

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Fetch Daily Sales Error")
        return {"error": str(e)}