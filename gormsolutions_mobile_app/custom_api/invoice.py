import frappe
import json

# @frappe.whitelist(allow_guest=True)
# def get_invoice_details(limit, offset, search=None):
#     filters = [["docstatus", "!=", 0]]

#     if search:
#         filters.append(["customer_name", "like", f"%{search}%"])

#     sales_invoice_details = frappe.get_all(
#         'Sales Invoice',
#         fields=['name', 'grand_total', 'paid_amount', 'outstanding_amount', 'docstatus',"status" ,'customer', 'customer_name', 'outstanding_amount'],
#         order_by='posting_date desc',
#         filters=filters,
#         start=offset,
#         page_length=limit
#     )

#     return sales_invoice_details

import frappe
from datetime import datetime, timedelta

import frappe
from datetime import datetime

@frappe.whitelist(allow_guest=True)
def get_invoice_details(limit, offset, search=None):
    # Initialize filters with docstatus filter
    filters = [["docstatus", "!=", 0]]

    # Add a filter for the logged-in user
    filters.append(["owner", "=", frappe.session.user])

    # If a search term is provided, add a filter for customer_name
    if search:
        filters.append(["customer_name", "like", f"%{search}%"])

    # Fetch filtered Sales Invoice details
    sales_invoice_details = frappe.get_all(
        'Sales Invoice',
        fields=[
            'name', 'grand_total', 'posting_time', 'posting_date', 'paid_amount', 'outstanding_amount',
            'owner', 'docstatus', "status", 'customer', 'customer_name'
        ],
        order_by='posting_date desc',
        filters=filters,
        start=offset,
        page_length=limit
    )

    # Format posting_time to include AM/PM and two decimal places for seconds
    for invoice in sales_invoice_details:
        if invoice.get('posting_time'):
            posting_time_str = str(invoice['posting_time'])

            # Ensure seconds are in two digits and fractional seconds are not more than two decimal places
            time_parts = posting_time_str.split(":")
            if len(time_parts) == 3:
                seconds_parts = time_parts[2].split(".")
                if len(seconds_parts) == 1:
                    # No decimal part, just ensure 2 digits for seconds
                    time_parts[2] = f"{seconds_parts[0]:02}"
                else:
                    # If there are decimals, ensure only two decimal places
                    time_parts[2] = f"{seconds_parts[0]:02}.{seconds_parts[1][:2]}"  # Limit to 2 decimals

            # Rebuild the time string after fixing the seconds and microseconds
            formatted_time_str = ":".join(time_parts)

            try:
                # Try parsing the fixed time with fractional seconds
                posting_time = datetime.strptime(formatted_time_str, '%H:%M:%S.%f')
                formatted_time = posting_time.strftime('%I:%M:%S.%f')[:-3]  # Trim microseconds to two decimals
                formatted_time = formatted_time + " " + posting_time.strftime("%p")
            except ValueError:
                # Fallback for cases where the format is not as expected
                posting_time = datetime.strptime(formatted_time_str, '%H:%M:%S')
                formatted_time = posting_time.strftime('%I:%M:%S') + " " + posting_time.strftime("%p")

            # Update the posting_time field with the formatted value
            invoice['posting_time'] = formatted_time

        # Fetch items related to each invoice
        items = frappe.get_all(
            'Sales Invoice Item',
            fields=['item_code', 'rate', 'qty', 'amount'],
            filters={'parent': invoice['name']}
        )
        invoice['items'] = items

    return sales_invoice_details


@frappe.whitelist()
def create_invoice(customer_name, paid_amount, items, user=None, is_pos=None, update_stock=None):
    import json

    # Parse items if necessary
    if isinstance(items, str):
        items = json.loads(items)

    # Get the current user
    current_user = frappe.session.user

    # Fetch User Permission records for 'Warehouse' allowed for the current user
    warehouse_list = frappe.get_all(
        'User Permission',
        filters={
            'user': current_user,
            'allow': 'Warehouse'
        },
        fields=['for_value']
    )
    
    # Determine fallback warehouse
    fallback_warehouse = warehouse_list[0]['for_value'] if warehouse_list else None

    if not fallback_warehouse:
        # Use the default warehouse from Stock Settings if no user permissions found
        fallback_warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse')
        if not fallback_warehouse:
            return {"error": "No warehouse assigned to user and no default warehouse found in Stock Settings."}

    # Fetch and validate Mode of Payment
    mode_of_payment_list = frappe.get_all(
        'User Permission',
        filters={
            'user': current_user,
            'allow': 'Mode of Payment'
        },
        fields=['for_value']
    )

    mode_of_payment = mode_of_payment_list[0]['for_value'] if mode_of_payment_list else None

    if not mode_of_payment:
        return {"error": "No Mode of Payment assigned to the user. Please configure Mode of Payment in User Permissions."}

    if not frappe.db.exists('Mode of Payment', mode_of_payment):
        return {"error": f"The Mode of Payment '{mode_of_payment}' does not exist in the system. Please check the configuration."}

    # Initialize POS profile and warehouse
    pos_profile = None
    pos_warehouse = None

    # If user and is_pos are provided, fetch POS profile
    if user and is_pos:
        pos_profile = frappe.db.get_value("POS Profile User", {"default": 1, "user": user}, "parent")
        pos_warehouse = frappe.db.get_value("POS Profile", pos_profile, "warehouse")

    # Set warehouse and enable update_stock if is_pos or update_stock is enabled
    if is_pos or update_stock:
        for item in items:
            # Use POS warehouse if available, else fallback to user-defined or default warehouse
            item['warehouse'] = pos_warehouse or fallback_warehouse
        update_stock = 1  # Explicitly enable update_stock

    try:
        # Construct the Sales Invoice document
        invoice_doc_data = {
            "doctype": "Sales Invoice",
            "customer": customer_name,
            "from_mobile_app": "Mobile App Cash Customer",
            "update_stock": update_stock,  # Ensure update_stock is enabled
            "is_pos": is_pos,  # Use the value passed by the user
            "items": items,
            "payment_terms_template": frappe.db.get_value("Customer", customer_name, "payment_terms") or None
        }

        # Include POS profile only if is_pos is enabled
        if is_pos:
            invoice_doc_data["pos_profile"] = pos_profile

            # Add payment details for POS invoices
            invoice_doc_data["payments"] = [{
                "mode_of_payment": mode_of_payment,
                "amount": paid_amount
            }]

        # Create the Sales Invoice document
        invoice_doc = frappe.get_doc(invoice_doc_data)

        # Save and submit the document
        res_doc = invoice_doc.insert()
        res_doc.submit()
        return res_doc

    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist()
def get_sales_payment_summary(start_date, end_date):
    try:
        # Get the logged-in user's full name
        user_doc = frappe.get_doc("User", frappe.session.user)
        user_full_name = user_doc.full_name

        # Fetch Sales Invoice total for the specified date range and creator, excluding cancelled records
        invoice_total = frappe.db.sql("""
            SELECT SUM(`tabSales Invoice`.grand_total) as total_amount
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %s AND %s
            AND docstatus = 1  # Exclude cancelled records (docstatus = 2)
            AND owner = %s
        """, (start_date, end_date, frappe.session.user))[0][0]

        # Fetch Payment Entry total for the specified date range linked to Sales Invoice and creator
        payment_total = frappe.db.sql("""
            SELECT SUM(`tabPayment Entry`.paid_amount) as total_paid_amount
            FROM `tabPayment Entry Reference`
            INNER JOIN `tabPayment Entry` ON `tabPayment Entry Reference`.parent = `tabPayment Entry`.name
            INNER JOIN `tabSales Invoice` ON `tabPayment Entry Reference`.reference_name = `tabSales Invoice`.name
            WHERE `tabPayment Entry`.posting_date BETWEEN %s AND %s
            AND `tabPayment Entry`.docstatus = 1  # Exclude cancelled records (docstatus = 2)
            AND `tabSales Invoice`.owner = %s
        """, (start_date, end_date, frappe.session.user))[0][0]

        data = {
            "user": user_full_name,
            "start_date": start_date,
            "end_date": end_date,
            "total_invoices": invoice_total,
            "total_payments": payment_total,
        }
        return data
    except Exception as e:
        return {"error": str(e)}
    
@frappe.whitelist(allow_guest=True)
def cancel_invoice(name=None):
    try:
        # Get the Sales Invoice document
        invoice_doc = frappe.get_doc("Sales Invoice", name)

        # Check if the invoice is already canceled
        if invoice_doc.docstatus == 2:  # 2 represents 'Cancelled'
            return {
                "message": "Invoice is already canceled",
                "status": "error"
            }

        # Cancel the invoice
        invoice_doc.cancel()

        return {
            "message": f"Invoice {name} has been canceled",
            "status": "success"
        }
    except Exception as e:
        return {
            "message": str(e),
            "status": "error"
        }


# @frappe.whitelist()
# def cancel_sales_invoice(docname):
#     invoice_doc = frappe.get_doc("Sales Invoice",docname)
#     return invoice_doc



@frappe.whitelist(allow_guest=True)
def get_sales_invoice(docname):
    invoice_doc = frappe.get_doc("Sales Invoice",docname)
    return invoice_doc

@frappe.whitelist()
def update_invoice(docname,items):
    invoice_doc = frappe.get_doc("Sales Invoice",docname)
    items = json.loads(items)
    for item in invoice_doc.items:
        for i in items:
            if item.item_code == i['item_code']:
                item.qty = i['qty']
    
        
    return invoice_doc.save(ignore_permissions=True)

@frappe.whitelist()
def get_sales_payment_summary(start_date, end_date):
    try:
        # Get the logged-in user's full name
        user_doc = frappe.get_doc("User", frappe.session.user)
        user_full_name = user_doc.full_name

        # Fetch Sales Invoice total for the specified date range, creator, and POS status (excluding cancelled records)
        invoice_total = frappe.db.sql("""
            SELECT SUM(`tabSales Invoice`.grand_total) as total_amount
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %s AND %s
            AND docstatus = 1  # Exclude cancelled records (docstatus = 2)
            AND owner = %s
            
        """, (start_date, end_date, frappe.session.user))[0][0]

        # Fetch Payment Entry total for the specified date range, linked to Sales Invoice and creator
        payment_total = frappe.db.sql("""
            SELECT SUM(`tabPayment Entry`.paid_amount) as total_paid_amount
            FROM `tabPayment Entry Reference`
            INNER JOIN `tabPayment Entry` ON `tabPayment Entry Reference`.parent = `tabPayment Entry`.name
            INNER JOIN `tabSales Invoice` ON `tabPayment Entry Reference`.reference_name = `tabSales Invoice`.name
            WHERE `tabPayment Entry`.posting_date BETWEEN %s AND %s
            AND `tabPayment Entry`.docstatus = 1  # Exclude cancelled records (docstatus = 2)
            AND `tabSales Invoice`.owner = %s
            """, (start_date, end_date, frappe.session.user))[0][0]

        # Add the paid_amount of the Sales Invoice records with is_pos = 1 directly
        invoice_paid_total = frappe.db.sql("""
            SELECT SUM(`tabSales Invoice`.paid_amount) as total_invoice_paid
            FROM `tabSales Invoice`
            WHERE posting_date BETWEEN %s AND %s
            AND docstatus = 1  # Exclude cancelled records (docstatus = 2)
            AND owner = %s
            AND is_pos = 1  # Include only POS invoices with a paid amount
        """, (start_date, end_date, frappe.session.user))[0][0]

        # Combine the Payment Entry total and the Invoice paid amounts
        total_payments = (payment_total or 0) + (invoice_paid_total or 0)

        # Prepare data to be returned
        data = {
            "user": user_full_name,
            "start_date": start_date,
            "end_date": end_date,
            "total_invoices": invoice_total if invoice_total else 0,
            "total_payments": total_payments,
        }
        return data
    except Exception as e:
        return {"error": str(e)}
