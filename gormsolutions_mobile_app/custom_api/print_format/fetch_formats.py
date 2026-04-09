import frappe

@frappe.whitelist()
def get_print_format_settings(user=None):
    current_user = user or frappe.session.user

    # Step 1: Fetch POS Profile for current user
    result = frappe.db.sql("""
        SELECT ppu.parent
        FROM `tabPOS Profile User` ppu
        JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
        WHERE ppu.user = %s AND ppu.default = 1 AND pp.disabled = 0
        LIMIT 1
    """, (current_user,), as_dict=0)

    if not result:
        return {"error": f"No enabled default POS Profile found for user '{current_user}'."}

    pos_profile = result[0][0]

    # Step 2: Get cost_center and company from POS Profile
    cost_center = frappe.db.get_value("POS Profile", pos_profile, "cost_center")
    company = frappe.db.get_value("POS Profile", pos_profile, "company")

    if not cost_center:
        return {"error": "Cost Center not found in POS Profile."}
    elif not company:
        return {"error": "Company not found in POS Profile."}

    # Step 3: Find matching Station Print Setting (parent) with child item row
    parent_name = frappe.db.sql("""
        SELECT psi.parent
        FROM `tabPrint Setting Item` psi
        WHERE psi.cost_center = %s AND psi.company = %s
        LIMIT 1
    """, (cost_center, company), as_dict=1)

    if not parent_name:
        return {"error": f"No Print Setting found for cost center '{cost_center}' and company '{company}'."}

    # Step 4: Load parent document with its children
    doc = frappe.get_doc("Station Print Setting", parent_name[0]["parent"])

    # Step 5: Find the matching child row
    item = next((i for i in doc.item if i.cost_center == cost_center and i.company == company), None)

    if not item:
        return {"error": "Matching Print Setting Item not found in Station Print Setting."}

    # Step 6: Construct and return response
    return {
        "cost_center": item.cost_center,
        "company": item.company,
        "format_header": item.format_header,
        "format_footer": item.format_footer,
        "default_customer": item.default_customer,
        "logo": item.logo,
        "barner": doc.barner  # ✅ Get barner from the parent doc
    }


import frappe

@frappe.whitelist()
def get_print_format_settings_company(user=None):
    current_user = user or frappe.session.user

    # Step 1: Fetch POS Profile for current user
    result = frappe.db.sql("""
        SELECT ppu.parent
        FROM `tabPOS Profile User` ppu
        JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
        WHERE ppu.user = %s AND ppu.default = 1 AND pp.disabled = 0
        LIMIT 1
    """, (current_user,), as_dict=0)

    if not result:
        return {"error": f"No enabled default POS Profile found for user '{current_user}'."}

    pos_profile = result[0][0]

    # Step 2: Get cost_center and company from POS Profile
    cost_center = frappe.db.get_value("POS Profile", pos_profile, "cost_center")
    company = frappe.db.get_value("POS Profile", pos_profile, "company")

    if not cost_center:
        return {"error": "Cost Center not found in POS Profile."}
    elif not company:
        return {"error": "Company not found in POS Profile."}

    # Step 3: Find parent Station Print Setting based on cost_center (child) and company (parent)
    parent_name = frappe.db.sql("""
        SELECT sps.name
        FROM `tabStation Print Setting` sps
        JOIN `tabPrint Setting Item` psi ON psi.parent = sps.name
        WHERE psi.cost_center = %s AND sps.company = %s
        LIMIT 1
    """, (cost_center, company), as_dict=1)

    if not parent_name:
        return {"error": f"No Station Print Setting found for cost center '{cost_center}' and company '{company}'."}

    # Step 4: Load parent document with its children
    doc = frappe.get_doc("Station Print Setting", parent_name[0]["name"])

    # Step 5: Find the matching child row
    item = next((i for i in doc.item if i.cost_center == cost_center), None)

    if not item:
        return {"error": "Matching Print Setting Item not found in Station Print Setting."}

    # Step 6: Construct and return response
    return {
        "cost_center": item.cost_center,
        "company": doc.company,  # from parent
        "format_header": item.format_header,
        "format_footer": item.format_footer,
        "default_customer": item.default_customer,
        "logo": item.logo,
        "barner": doc.barner
    }
