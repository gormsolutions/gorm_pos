import frappe

@frappe.whitelist()
def get_item_suppliers_with_email(item_code, existing_suppliers=None):
    """
    Given an item code, return a list of supplier dicts (supplier, email_id, mobile_no)
    only for suppliers not already in existing_suppliers.
    """
    existing_suppliers = frappe.parse_json(existing_suppliers or "[]")

    item = frappe.get_doc("Item", item_code)
    results = []

    for entry in item.supplier_items:
        supplier = entry.supplier

        if supplier in existing_suppliers:
            continue

        contact_name = frappe.db.get_value(
            "Dynamic Link",
            {
                "link_doctype": "Supplier",
                "link_name": supplier,
                "parenttype": "Contact"
            },
            "parent"
        )

        email = ""
        mobile_no = ""
        if contact_name:
            contact = frappe.db.get_value(
                "Contact",
                contact_name,
                ["email_id", "mobile_no"],
                as_dict=True
            )
            if contact:
                email = contact.email_id or ""
                mobile_no = contact.mobile_no or ""

        results.append({
            "supplier": supplier,
            "email_id": email,
            "mobile_no": mobile_no
        })

    return results
