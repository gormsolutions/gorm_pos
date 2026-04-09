import frappe

@frappe.whitelist()
def get_user_companies():
    """Return the list of companies the current user has permission for."""
    user = frappe.session.user

    # get permitted companies
    companies = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Company"},
        fields=["for_value"]
    )

    # fallback: all companies if none found
    if not companies:
        companies = frappe.get_all("Company", pluck="name")
    else:
        companies = [c.for_value for c in companies if c.for_value]

    return companies
