# import frappe
# from frappe import _

# @frappe.whitelist(allow_guest=True)
# def get_all_payment_modes():
#     try:
#         # Get the current user
#         current_user = frappe.session.user

#         # Deny access to guests
#         if current_user == "Guest":
#             frappe.throw(_("You must be logged in to access payment modes."), frappe.PermissionError)

#         # Fetch User Permission records for 'Mode of Payment' allowed for the current user
#         user_permission_records = frappe.get_all(
#             'User Permission',
#             filters={
#                 'user': current_user,
#                 'allow': 'Mode of Payment'
#             },
#             fields=['for_value']
#         )

#         # Extract allowed Mode of Payment names
#         allowed_mode_names = [record['for_value'] for record in user_permission_records]

#         # Define filters to fetch enabled 'Mode of Payment'
#         filters = {'enabled': 1}

#         # Apply User Permission filter if applicable
#         if allowed_mode_names:
#             filters['name'] = ['in', allowed_mode_names]

#         # Fetch filtered Mode of Payment records
#         mode_of_payment_list = frappe.get_all('Mode of Payment', filters=filters, fields=['name'])

#         # Format the response using 'mode_of_payment' key
#         mode_of_payments = [{'name': mode.get('name')} for mode in mode_of_payment_list]

#         return mode_of_payments

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Mode of Payment Error")
#         return {"error": str(e)}

import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_all_payment_modes():
    try:
        current_user = frappe.session.user

        if current_user == "Guest":
            frappe.throw(_("You must be logged in to access payment modes."), frappe.PermissionError)

        # Get allowed Mode of Payment names from User Permission
        user_permission_records = frappe.get_all(
            'User Permission',
            filters={
                'user': current_user,
                'allow': 'Mode of Payment'
            },
            fields=['for_value']
        )
        allowed_mode_names = [record['for_value'] for record in user_permission_records]

        filters = {'enabled': 1}
        if allowed_mode_names:
            filters['name'] = ['in', allowed_mode_names]

        # Fetch Mode of Payment records
        mode_of_payment_list = frappe.get_all(
            'Mode of Payment',
            filters=filters,
            fields=['name']
        )

        # Final list to return
        mode_of_payments = []

        for mode in mode_of_payment_list:
            mop_name = mode.get("name")

            # Fetch the default account from Mode of Payment Account table (assuming first available one)
            mop_account = frappe.get_all(
                'Mode of Payment Account',
                filters={'parent': mop_name},
                fields=['default_account'],
                limit=1
            )

            account_name = mop_account[0]['default_account'] if mop_account else None
            account_type = None

            if account_name:
                account_type = frappe.db.get_value('Account', account_name, 'account_type')

            mode_of_payments.append({
                'name': mop_name,
                'default_account': account_name,
                'account_type': account_type
            })

        return mode_of_payments

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Mode of Payment Error")
        return {"error": str(e)}
