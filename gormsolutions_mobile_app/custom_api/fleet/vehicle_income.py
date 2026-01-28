import frappe
from frappe.utils import flt
from frappe import _

@frappe.whitelist()
def submit_vehicle_income(data):
    """
    data: JSON string of Vehicle Income including items
    Example: data='{"vehicle":"UBG968W", ... }'
    """
    import json
    if isinstance(data, str):
        data = json.loads(data)

    # Now create Vehicle Income doc
    items = data.pop("items", [])

    doc = frappe.get_doc({
        "doctype": "Vehicle Income",
        **data
    })

    for item in items:
        doc.append("items", item)

    # Insert & Submit
    doc.insert(ignore_permissions=True)
    doc.submit()

    return {
        "status": "success",
        "vehicle_income": doc.name,
        "sales_invoice": doc.sales_invoice,
        "payment_entry": getattr(doc, "payment_entry", None)
    }
