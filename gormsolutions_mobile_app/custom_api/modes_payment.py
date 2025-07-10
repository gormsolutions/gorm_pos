import frappe

from frappe import _

@frappe.whitelist(allow_guest=True)
def get_all_payment_modes():
    try:
        current_user = frappe.session.user

        # Search for POS Profiles where current user is listed in 'applicable_for_users' child table
        pos_profiles = frappe.get_all("POS Profile", filters={"disabled": 0}, fields=["name"])

        pos_profile_name = None
        for profile in pos_profiles:
            user_found = frappe.get_all(
                "POS Profile User",
                filters={"parent": profile.name, "user": current_user},
                limit=1
            )
            if user_found:
                pos_profile_name = profile.name
                break

        if not pos_profile_name:
            return []

        # Get POS Profile document
        pos_profile = frappe.get_doc("POS Profile", pos_profile_name)

        # Extract mode of payments from 'POS Payment Method' child table
        mode_of_payments = [
            {"name": row.mode_of_payment}
            for row in pos_profile.payments
            if row.mode_of_payment
        ]

        return mode_of_payments

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Mode of Payment Error")
        return {"error": str(e)}

