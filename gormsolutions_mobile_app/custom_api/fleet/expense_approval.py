import frappe
from frappe import _

@frappe.whitelist()
def update_expense_claim(expense_claim_name, updates):
    """
    Update allowed fields of a Draft Expense Claim using Frappe doc API.
    Only Draft Expense Claims (docstatus=0) can be updated.
    Updates are matched based on 'description' for Vehicle Expenses.

    Args:
        expense_claim_name (str): Name of the Expense Claim
        updates (dict): key-value pairs of fields to update
            For child table, use:
            "expenses": [{"description": "Fuel", "amount": 50000}, ...]
    
    Returns:
        dict: updated Expense Claim data
    """
    import json
    if isinstance(updates, str):
        updates = json.loads(updates)

    # Load parent doc
    doc = frappe.get_doc("Expense Claim", expense_claim_name)

    # Only Draft allowed
    if doc.docstatus != 0:
        frappe.throw(_("Only Draft Expense Claims can be updated."))

    # Update parent fields
    for field in ["expense_approver", "approval_status"]:
        if field in updates:
            setattr(doc, field, updates[field])

    # Update child table 'expenses'
    if "expenses" in updates:
        vehicle_rows = [r for r in doc.expenses if r.expense_type == "Vehicle Expenses"]

        # Map existing rows by description for quick lookup
        row_map = {r.description: r for r in vehicle_rows}

        for new_values in updates["expenses"]:
            desc = new_values.get("description")
            if not desc:
                frappe.throw(_("Each expense row must have 'description'."))
            if desc not in row_map:
                frappe.throw(_("No Vehicle Expense row found with description '{0}'").format(desc))

            row_doc = row_map[desc]
            if "amount" not in new_values:
                frappe.throw(_("Each expense row must have 'amount'."))
            row_doc.amount = new_values["amount"]
            row_doc.sanctioned_amount = new_values["amount"]  # optional

    # Save the document
    doc.save(ignore_permissions=True)

    # Return updated doc
    return {
        "name": doc.name,
        "employee": doc.employee,
        "expense_approver": doc.expense_approver,
        "approval_status": doc.approval_status,
        "docstatus": doc.docstatus,
        "expenses": [{"description": r.description, "amount": r.amount, "sanctioned_amount": r.sanctioned_amount, "expense_type": r.expense_type} for r in doc.expenses],
        "message": _("Expense Claim updated successfully.")
    }
