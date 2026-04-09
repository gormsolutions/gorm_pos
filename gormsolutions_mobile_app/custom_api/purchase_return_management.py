import frappe
from frappe import _

import frappe
from frappe import _

@frappe.whitelist()
def get_invoice_items(purchase_invoice):
    # Fetch the Purchase Invoice document
    invoice = frappe.get_doc("Purchase Invoice", purchase_invoice)

    # Collect all items from the Purchase Invoice
    items = []
    for item in invoice.items:
        items.append({
            'item_code': item.item_code,
            'qty': item.qty,
            'rate': item.rate,
            'uom': item.uom,
            'warehouse': item.warehouse
        })
    
    # Return items and the posting_date
    return {
        "items": items,
        "posting_date": invoice.posting_date,
        "status": invoice.status,
        "return_against":invoice.return_against
    }


import frappe
from frappe.model.document import Document

@frappe.whitelist()
def create_purchase_invoice(docname):
    # Fetch the Purchase Return Management document
    doc = frappe.get_doc("Purchase Return Management", docname)

    # Create a new Purchase Invoice
    purchase_invoice = frappe.new_doc("Purchase Invoice")
    purchase_invoice.supplier = doc.supplier
    purchase_invoice.posting_date = doc.posting_date
    purchase_invoice.due_date = doc.posting_date  # Assuming due date is same as posting date, can be changed
    purchase_invoice.update({
        "custom_suplier_return_id": doc.name  # Reference to the Purchase Return Management
    })

    # Loop through the return_items child table and add items to the Purchase Invoice
    for item in doc.return_items:
        # Check if qty is negative, and change it to positive
        qty = abs(item.qty)  # Convert negative qty to positive

        purchase_invoice.append("items", {
            "item_code": item.item_code,
            "qty": qty,
            "rate": item.rate,
            "uom": item.uom,
            "warehouse": item.warehouse
        })

    # Submit the Purchase Invoice
    purchase_invoice.insert()
    purchase_invoice.submit()

    # Update the supplier_return_status field to 'Compensated' on Purchase Return Management
    doc.supplier_return_status = "Compensated"
    doc.save()

    return purchase_invoice.name  # Return the name of the created Purchase Invoice
