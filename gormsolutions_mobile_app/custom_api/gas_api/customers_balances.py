import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_gas_customer_financials_with_items():
    customers = frappe.get_all(
        "Customer",
        filters={"custom_customer_category": "Gas Customer"},
        fields=["name", "customer_name", "territory"]
    )

    final_data = []

    for cust in customers:
        # Fetch all invoices
        invoices_raw = frappe.get_all(
            "Sales Invoice",
            filters={"customer": cust.name, "docstatus": 1},
            fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status"]
        )

        invoices = []
        total_invoiced = 0
        total_outstanding = 0

        for inv in invoices_raw:
            # Fetch items for each invoice
            items = frappe.get_all(
                "Sales Invoice Item",
                filters={"parent": inv.name},
                fields=["item_code", "item_name", "qty", "rate", "amount"]
            )

            invoices.append({
                "invoice_name": inv.name,
                "posting_date": inv.posting_date,
                "due_date": inv.due_date,
                "grand_total": inv.grand_total,
                "outstanding_amount": inv.outstanding_amount,
                "status": inv.status,
                "items": items
            })

            total_invoiced += flt(inv.grand_total)
            total_outstanding += flt(inv.outstanding_amount)

        # Fetch payments
        payments = frappe.get_all(
            "Payment Entry",
            filters={"party": cust.name, "party_type": "Customer", "docstatus": 1},
            fields=["name", "posting_date", "paid_amount", "reference_no", "payment_type", "reference_date"]
        )

        total_paid = sum(flt(p.paid_amount) for p in payments)

        final_data.append({
            "customer_name": cust.customer_name,
            "customer_id": cust.name,
            "territory": cust.territory,
            "summary": {
                "total_invoiced": total_invoiced,
                "total_paid": total_paid,
                "total_outstanding": total_outstanding,
                "final_balance": total_invoiced - total_paid
            },
            "invoices": invoices,
            "payments": payments
        })

    return final_data
