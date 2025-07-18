import frappe
from frappe.utils import cint

@frappe.whitelist()
def create_user_permissions_from_stock_transfer_setting(docname):
    """
    Creates User Permission records from rows in the 'items' child table
    of the given Stock Transfer Setting document.
    Only processes rows where posted != 1.
    """
    doc = frappe.get_doc("Stock Transfer Setting", docname)
    has_changes = False

    for row in doc.get("items"):
        if cint(row.posted) == 1 or not row.user:
            continue

        permission_created = False

        if row.cost_center:
            permission_created |= _create_permission_if_not_exists(
                doctype="Cost Center",
                for_value=row.cost_center.strip(),
                user=row.user.strip(),
                is_default=row.default
            )

        if row.warehouse:
            permission_created |= _create_permission_if_not_exists(
                doctype="Warehouse",
                for_value=row.warehouse.strip(),
                user=row.user.strip(),
                is_default=row.default
            )

        # Mark row as posted if permission was created
        if permission_created:
            row.posted = 1
            has_changes = True

    if has_changes:
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.msgprint("Permissions created and rows updated.")

def _create_permission_if_not_exists(doctype, for_value, user, is_default):
    """
    Creates a User Permission if it doesn't already exist.
    Returns True if permission was created or updated.
    """
    if not user or not for_value:
        return False

    if not frappe.db.exists(doctype, for_value):
        frappe.msgprint(f"Skipping: {doctype} '{for_value}' does not exist.")
        return False

    existing = frappe.get_all("User Permission", filters={
        "user": user,
        "allow": doctype,
        "for_value": for_value
    }, fields=["name", "is_default"])

    if existing:
        if cint(is_default) and not existing[0]["is_default"]:
            perm = frappe.get_doc("User Permission", existing[0]["name"])
            perm.is_default = 1
            perm.save(ignore_permissions=True)
            return True
        return False

    perm = frappe.new_doc("User Permission")
    perm.user = user
    perm.allow = doctype
    perm.for_value = for_value
    perm.is_default = cint(is_default)
    perm.insert(ignore_permissions=True)
    return True


import frappe
from frappe import _
from frappe.utils import cint

def validate_user_stock_transfer(doc, method):
    if doc.purpose != "Material Transfer":
        return  # Only apply to Material Transfer entries

    user = frappe.session.user

    # Only apply restriction if user has the "Transfer Permit" role
    if not frappe.has_role(user, "Transfer Permit"):
        return

    # Get all warehouse permissions where is_default == 1
    user_perms = frappe.get_all("User Permission", filters={
        "user": user,
        "allow": "Warehouse"
    }, fields=["for_value", "is_default"])

    default_warehouses = {p.for_value for p in user_perms if cint(p.is_default) == 1}

    for item in doc.items:
        target = item.t_warehouse

        # Block if target warehouse is not in the user's default warehouses
        if target and target not in default_warehouses:
            frappe.throw(_(
                f"You are not allowed to submit a Stock Transfer to Target Warehouse <b>{target}</b>. "
                "Please contact your administrator to request access."
            ), title=_("Not Allowed"))
