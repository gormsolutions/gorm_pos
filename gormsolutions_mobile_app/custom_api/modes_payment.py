import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_all_payment_modes():
    try:
        # Get the current user
        current_user = frappe.session.user

        # Deny access to guests
        if current_user == "Guest":
            frappe.throw(_("You must be logged in to access payment modes."), frappe.PermissionError)

        # Fetch User Permission records for 'Mode of Payment' allowed for the current user
        user_permission_records = frappe.get_all(
            'User Permission',
            filters={
                'user': current_user,
                'allow': 'Mode of Payment'
            },
            fields=['for_value']
        )

        # Extract allowed Mode of Payment names
        allowed_mode_names = [record['for_value'] for record in user_permission_records]

        # Define filters to fetch enabled 'Mode of Payment'
        filters = {'enabled': 1}

        # Apply User Permission filter if applicable
        if allowed_mode_names:
            filters['name'] = ['in', allowed_mode_names]

        # Fetch filtered Mode of Payment records
        mode_of_payment_list = frappe.get_all('Mode of Payment', filters=filters, fields=['name'])

        # Format the response using 'mode_of_payment' key
        mode_of_payments = [{'name': mode.get('name')} for mode in mode_of_payment_list]

        return mode_of_payments

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Mode of Payment Error")
        return {"error": str(e)}
