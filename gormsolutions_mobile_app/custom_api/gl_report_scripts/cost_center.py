import frappe

@frappe.whitelist()
def get_company_accounts(company=None, txt=""):
    """
    Fetch Accounts for a given company.
    Returns a list of dicts for autocomplete/search.
    """
    if not company:
        return []

    accounts = frappe.db.get_all(
        "Account",
        filters={"company": company, "is_group": 0},
        fields=["name"],
        order_by="name"
    )

    # Return as a list of dicts for your frontend autocomplete
    return [{"value": a.name} for a in accounts if txt.lower() in a.name.lower()]
@frappe.whitelist()
def get_company_cost_centers(company=None, txt=""):
    if not company:
        return []

    centers = frappe.db.get_all(
        "Cost Center",
        filters={"company": company, "is_group": 0},
        fields=["name"],
        order_by="name"
    )
    return [{"value": c.name} for c in centers if txt.lower() in c.name.lower()]


# -------------------------------
# Party (Customer/Supplier/Employee) dynamically

# gormsolutions_mobile_app/custom_api/gl_report_scripts/party_queries.py
import frappe

# @frappe.whitelist()
# def get_parties(party_type=None, txt=None, start=0, page_len=20, filters=None):
#     """
#     Returns a list of parties (Customer or Supplier) for autocomplete search.
#     """
#     if party_type not in ("Customer", "Supplier"):
#         return []

#     search_filters = {}
#     if txt:
#         search_filters["name"] = ["like", f"%{txt}%"]

#     # Optionally filter by company if filters dict exists
#     if filters and filters.get("company"):
#         search_filters["company"] = filters["company"]

#     parties = frappe.get_all(
#         party_type,
#         filters=search_filters,
#         fields=["name"],
#         limit_start=start,
#         limit_page_length=page_len,
#         order_by="name"
#     )

#     # Convert to format for Frappe link search
#     return [{"value": p["name"], "description": p["name"]} for p in parties]


@frappe.whitelist()
def get_parties(party_type=None, txt=None, start=0, page_len=20, filters=None):

    if party_type not in ("Customer", "Supplier"):
        return []

    search_filters = {}
    or_filters = []

    # Search logic
    if txt:
        if party_type == "Customer":
            or_filters = [
                ["name", "like", f"%{txt}%"],
                ["customer_name", "like", f"%{txt}%"]
            ]
        elif party_type == "Supplier":
            or_filters = [
                ["name", "like", f"%{txt}%"],
                ["supplier_name", "like", f"%{txt}%"]
            ]

    # Optional company filter
    if filters and filters.get("company"):
        search_filters["company"] = filters["company"]

    parties = frappe.get_all(
        party_type,
        filters=search_filters,
        or_filters=or_filters,
        fields=["name", 
                "customer_name" if party_type == "Customer" else "supplier_name"],
        limit_start=start,
        limit_page_length=page_len,
        order_by="name"
    )

    # Format nicely (show real name + ID)
    result = []
    for p in parties:
        display_name = (
            p.get("customer_name") or p.get("supplier_name") or p["name"]
        )
        result.append({
            "value": p["name"],
            "description": f"{display_name} ({p['name']})"
        })

    return result