import frappe
from frappe.utils import flt, today

@frappe.whitelist()
def get_vehicle_income_report(from_date=None, to_date=None):
    """
    Fetch all Vehicle Income entries with linked Sales Invoice and Payment Entry
    """
    filters = [["docstatus", "=", 1]]  # Only submitted
    if from_date and to_date:
        filters.append(["date", ">=", from_date])
        filters.append(["date", "<=", to_date])

    vehicle_entries = frappe.get_all(
        "Vehicle Income",
        filters=filters or None,
        fields=[
            "name",
            "vehicle",
            "vehicle_name",
            "driver",
            "driver_name",
            "customer",
            "date",
            "total_amount",
            "is_paid",
            "sales_invoice",
            "payment_entry",
            "mode_of_payment",
            "cost_center"
        ],
        order_by="date desc"
    )

    report = []

    for ve in vehicle_entries:
        # Fetch items for each Vehicle Income
        items = frappe.get_all(
            "Vehicle Income Item",
            filters={"parent": ve.name},
            fields=["vehicle as item_name", "qty", "rate", "amount"]
        )

        report.append({
            "vehicle_income": ve.name,
            "vehicle": ve.vehicle,
            "vehicle_name": ve.vehicle_name,
            "driver": ve.driver,
            "driver_name": ve.driver_name,
            "customer": ve.customer,
            "date": ve.date,
            "total_amount": flt(ve.total_amount),
            "is_paid": ve.is_paid,
            "mode_of_payment": ve.mode_of_payment,
            "cost_center": ve.cost_center,
            "sales_invoice": ve.sales_invoice,
            "payment_entry": ve.payment_entry,
            "items": items
        })

    return report
