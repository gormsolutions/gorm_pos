import frappe

def block_unauthorized_creation(doc, method):

    # Users allowed to create Sales Invoices manually
    allowed_users = [
        "Administrator",
        "manager.ph@divacakes.com.ng",
        "nwokeocha.lucy@divacakes.com.ng",
        "it@divacakes.com.ng",
        "cso.gbagada@divacakes.com.ng",
        "manager.satellite@divacakes.com.ng"
    ]

    current_user = frappe.session.user

    # CASE 1 — Allowed users can create invoices normally
    if current_user in allowed_users:
        return

    # CASE 2 — Everyone else must have custom_from = 'GormPos'
    si_from = (doc.get("custom_from") or "").strip()

    if si_from != "GormPos":
        frappe.throw(
            "You are not allowed to create Sales Invoice manually. "
            "Please use the Gorm POS.",
            frappe.PermissionError
        )
