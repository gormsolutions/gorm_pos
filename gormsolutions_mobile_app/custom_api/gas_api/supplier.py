import frappe

@frappe.whitelist()
def get_suppliers(search=None):
    filters = {}
    if search:
        filters["supplier_name"] = ["like", f"%{search}%"]

    suppliers = frappe.get_all(
        "Supplier",
        filters=filters,
        fields=["name"]
    )

    return suppliers


import frappe

@frappe.whitelist()
def get_expense_claim_types():
    """Return all Expense Claim Types."""
    claim_types = frappe.get_all(
        "Expense Claim Type",
        fields=["name"]
    )
    return claim_types

