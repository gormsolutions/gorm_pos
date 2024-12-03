import frappe
import json

@frappe.whitelist(allow_guest=True)
def create_payment(sales_invoice,mode_of_payment,paid_amount):
    mode_of_pay_doc = frappe.get_doc("Mode of Payment",mode_of_payment)
    sales_invoice_doc = frappe.get_doc("Sales Invoice",sales_invoice)
    # return mode_of_pay_doc.accounts[0].default_account,sales_invoice.customer
        
    try:
        payment_doc = frappe.get_doc({
            "doctype":"Payment Entry",
            "payment_type":"Receive",
            "party_type":"Customer",
            "party":sales_invoice_doc.customer,
            "mode_of_payment":mode_of_payment,
            "paid_to":mode_of_pay_doc.accounts[0].default_account,
            "paid_amount":paid_amount,
            "received_amount":paid_amount,
            "references":[{
                "reference_doctype":"Sales Invoice",
                "reference_name":sales_invoice,
                "allocated_amount":paid_amount
            }]
        })
        
        res_doc = payment_doc.insert(ignore_permissions=True)
        res_doc.submit()

        return {"total":res_doc.references[0].total_amount,"outstanding_amount":res_doc.references[0].outstanding_amount,"paid_amount":res_doc.references[0].allocated_amount}
    except Exception as e:
        return e

# @frappe.whitelist(allow_guest=True)
# def get_mode_of_payment():
#     mode_of_pay_list = frappe.get_all('Mode of Payment',
#     filters={"enabled":1},
#     fields=['name'])
#     return mode_of_pay_list

@frappe.whitelist(allow_guest=True)
def mode_of_payment():
    try:
        # Get the current user
        current_user = frappe.session.user

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

        # Extract and format the list
        mode_of_payments = [{'name': mode.get('name')} for mode in mode_of_payment_list]

        return mode_of_payments
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Mode of Payment Error")
        return {"error": str(e)}
