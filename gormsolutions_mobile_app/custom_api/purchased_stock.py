import frappe
@frappe.whitelist(allow_guest=True)
def receive_payment_and_create_invoice(party=None, mode_of_payment=None, paid_amount=0, posting_date=None, invoice_items=None):
    if not party or not posting_date or not invoice_items:
        return {"error": "Party, posting date, and invoice items are required."}
    
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
        
        # If payment data is provided, create the Payment Entry
        payment_doc = None
        if mode_of_payment and paid_amount:
            # Fetch default account from the Mode of Payment
            mode_of_pay_doc = frappe.get_doc("Mode of Payment", mode_of_payment)
            default_account = mode_of_pay_doc.accounts[0].default_account if mode_of_pay_doc.accounts else None
            
            if not default_account:
                return {"error": "No default account found for the selected mode of payment."}
            
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
            })
            
            payment_doc.insert(ignore_permissions=True)
            payment_doc.submit()
        
        # Create Purchase Invoice
        customer_name = frappe.get_value("Customer", party, "customer_name")
        if not customer_name:
            return {"error": f"No customer found for the party '{party}'."}

        # Create the Purchase Invoice and add items directly
        invoice_doc = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": party,
            "supplier_name": customer_name,
            "posting_date": posting_date,
            "due_date": posting_date,  # Due date can be same as posting date or as required
        })
        
        # Add items to the invoice dynamically
        if isinstance(invoice_items, list):  # Ensure invoice_items is a list
            for item in invoice_items:
                invoice_doc.append("items", {
                    "item_code": item.get("item_code"),
                    "qty": item.get("qty"),
                    "rate": item.get("rate"),
                    "amount": item.get("amount"),
                    "cost_center": default_cost_centers[0]  # Set the default cost center
                })
        else:
            # If only one item, add directly
            invoice_doc.append("items", {
                "item_code": invoice_items.get("item_code"),
                "qty": invoice_items.get("qty"),
                "rate": invoice_items.get("rate"),
                "amount": invoice_items.get("amount"),
                "cost_center": default_cost_centers[0]  # Set the default cost center
            })
        
        # Insert and submit the Purchase Invoice
        invoice_doc.insert(ignore_permissions=True)
        invoice_doc.submit()
        
        # Return response with success message and the relevant details
        return {
            "message": "success",
            "invoice_number": invoice_doc.name,
            "payment_doc": payment_doc.name if payment_doc else None,  # Only return payment doc if it exists
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Payment and Invoice Error")
        return {"error": str(e)}
