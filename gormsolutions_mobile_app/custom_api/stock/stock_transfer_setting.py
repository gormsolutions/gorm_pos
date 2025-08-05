import frappe
from frappe import _
from frappe.utils import cint

def validate_user_stock_transfer(doc, method):
    if doc.purpose != "Material Transfer":
        return

    user = frappe.session.user

    # Only enforce if the user has the "Transfer Permit" role
    if "Transfer Permit" not in frappe.get_roles(user):
        return

    # Get the user's default warehouse
    default_perm = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Warehouse",
            "is_default": 1
        },
        fields=["for_value"],
        limit=1
    )

    # if not default_perm:
    #     frappe.throw(_("No default warehouse found for your user permissions. Contact Administrator."))

    default_warehouse = default_perm[0].for_value

    for item in doc.items:
        source_warehouse = item.s_warehouse

        if source_warehouse != default_warehouse:
            # Find users permitted for this warehouse
            permitted_users = frappe.get_all(
                "User Permission",
                filters={
                    "allow": "Warehouse",
                    "for_value": source_warehouse,
                    "is_default": 1
                },
                fields=["user"]
            )

            # Fetch full names
            full_names = []
            for pu in permitted_users:
                full_name = frappe.db.get_value("User", pu.user, "full_name")
                if full_name:
                    full_names.append(full_name)

            contact_info = ", ".join(full_names) if full_names else _("No user found")

            frappe.throw(_(
                f"You are not allowed Update this stock transfer.<b>Click Active button to reject with the reason </b><br>"
                f"Please contact the permitted user(s): <b>{contact_info}</b> ."
            ), title=_("Warehouse Restriction"))

# In gormsolutions_mobile_app/custom_api/stock/stock_transfer_setting.py
# File: gormsolutions_mobile_app/custom_api/stock/stock_transfer_setting.py


def validate_user_stock_transfer_source_warehouse(doc, method):
    if doc.purpose != "Material Transfer":
        return

    user = frappe.session.user

    if "Transfer Permit" not in frappe.get_roles(user):
        return
    
    if doc.custom_approve_status != "Approved":
        frappe.throw("Please Approve the Stock Transfer.")


    # Get user's default warehouse
    default_perm = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Warehouse",
            "is_default": 1
        },
        fields=["for_value"],
        limit=1
    )

    # if not default_perm:
    #     frappe.throw(_("No default warehouse found for your user permissions. Contact Administrator."))


    default_warehouse = default_perm[0].for_value

    for item in doc.items:
        source_warehouse = item.s_warehouse

        # ❌ Restrict if user is trying to transfer from their default warehouse
        if source_warehouse == default_warehouse:
            # Find other permitted users for that warehouse
            permitted_users = frappe.get_all(
                "User Permission",
                filters={
                    "allow": "Warehouse",
                    "for_value": source_warehouse,
                    "is_default": 0,
                    "user": ["!=", user]  # exclude current user
                },
                fields=["user"]
            )

            # Get their full names
            full_names = []
            for pu in permitted_users:
                full_name = frappe.db.get_value("User", pu.user, "full_name")
                if full_name:
                    full_names.append(full_name)

            contact_info = ", ".join(full_names) if full_names else _("No other permitted users found.")

            frappe.throw(_(
                f"You are not allowed to Submit this stock transfer.<br>"
                f"Contact Permitted users for this warehouse: <b>{contact_info}</b>."
            ), title=_("Warehouse Restriction"))



@frappe.whitelist()
def reject_stock_entry(docname, reason):
    if not docname or not reason:
        frappe.throw(_("Missing parameters."))

    # Update fields directly in DB
    frappe.db.sql("""
        UPDATE `tabStock Entry`
        SET custom_approve_status = %s,
            custom_reason = %s
        WHERE name = %s
    """, ("Rejected", reason, docname))

    frappe.db.commit()
    

@frappe.whitelist()
def approve_stock_entry(docname):
    if not docname:
        frappe.throw(_("Missing document name."))

    frappe.db.sql("""
        UPDATE `tabStock Entry`
        SET custom_approve_status = %s,
            custom_reason = NULL
        WHERE name = %s
    """, ("Approved", docname))
    frappe.db.commit()


def validate_before_submit(doc, method):
    if doc.custom_approve_status == "Rejected":
        frappe.throw("You cannot submit a rejected Stock Entry.")


import frappe

@frappe.whitelist()
def assign_transfer_permit_to_all_users():
    role_name = "Transfer Permit"
    
    # Ensure the role exists
    if not frappe.db.exists("Role", role_name):
        frappe.throw(f"Role '{role_name}' does not exist. Please create it first.")
    
    # Get all enabled system users
    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        pluck="name"
    )

    assigned_count = 0

    for user in users:
        # Check if user already has the role
        if not frappe.db.exists("Has Role", {"parent": user, "role": role_name}):
            user_doc = frappe.get_doc("User", user)
            user_doc.append("roles", {"role": role_name})
            user_doc.flags.ignore_permissions = True
            user_doc.save()
            assigned_count += 1

    frappe.db.commit()

    return f"Assigned '{role_name}' role to {assigned_count} user(s)."


# def set_pending_approval(doc, method):
#     if doc.purpose == "Material Transfer" and not doc.custom_approve_status:
#         doc.custom_approve_status = "Pending Approval"
