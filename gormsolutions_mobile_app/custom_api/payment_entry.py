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

@frappe.whitelist()
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

@frappe.whitelist(allow_guest=True)
def receive_payment(party=None, mode_of_payment=None, paid_amount=0, posting_date=None, reference_no=None, reference_date=None):
    if not party or not mode_of_payment or not paid_amount or not posting_date:
        return {"error": "Party, mode of payment, paid amount, and posting date are required."}
    
    try:
        # Fetch allowed Cost Centers for the current user
        current_user = frappe.session.user
        cost_center_permitted = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Cost Center"},
            fields=["for_value"]
        )
        default_cost_centers = [perm["for_value"] for perm in cost_center_permitted]
        
        if not default_cost_centers:
            return {"error": "No permitted cost centers found for the current user."}
        
        # Fetch default account from the Mode of Payment
        mode_of_pay_doc = frappe.get_doc("Mode of Payment", mode_of_payment)
        default_account = mode_of_pay_doc.accounts[0].default_account if mode_of_pay_doc.accounts else None
        
        if not default_account:
            return {"error": "No default account found for the selected mode of payment."}
        
        # Check if the Default Account is of Account Type 'Bank'
        account_doc = frappe.get_doc("Account", default_account)
        if account_doc.account_type == "Bank" and (not reference_no or not reference_date):
            return {"error": "Reference No and Reference Date are mandatory for transactions involving bank accounts."}
        
        # Fetch Customer Name
        customer_name = frappe.get_value("Customer", party, "customer_name")
        if not customer_name:
            return {"error": f"No customer found for the party '{party}'."}
        
        # Create Payment Entry
        payment_doc = frappe.get_doc({
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "party_type": "Customer",
            "cost_center": default_cost_centers[0],  # Use the first permitted cost center
            "party": party,
            "party_name": customer_name,
            "mode_of_payment": mode_of_payment,
            "paid_to": default_account,
            "paid_amount": paid_amount,
            "received_amount": paid_amount,
            "posting_date": posting_date,  # Set the posting date
            "reference_no": reference_no,  # Include Reference No
            "reference_date": reference_date,  # Include Reference Date
        })
        
        payment_doc.insert(ignore_permissions=True)
        payment_doc.submit()
        
        return {
            "message": "success",
            "customer_name": customer_name,
            "paid_amount": payment_doc.paid_amount,
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Payment Error")
        return {"error": str(e)}
