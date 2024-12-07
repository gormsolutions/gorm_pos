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
            'name', 'grand_total','posting_date', 'paid_amount', 'outstanding_amount','owner', 
            'docstatus', "status", 'customer', 'customer_name', 'outstanding_amount'
        ],
        order_by='posting_date desc',
        filters=filters,
        start=offset,
        page_length=limit
    )

    return sales_invoice_details


# @frappe.whitelist()
# def create_invoice(customer_name,paid_amount,items,user=None):
    
#     items = json.loads(items)
#     pos_profile = None
#     if user:
#         pos_profile = frappe.db.get_value("POS Profile User",{"default":1,"user":user},"parent")
#         pos_warehouse = frappe.db.get_value("POS Profile",pos_profile,"warehouse")
#         for item in items:
#             item['warehouse'] = pos_warehouse

#     # return items
    
#     try:
#         # items = [{
#         # "item_code": "apple-15",
#     	#  "qty": 16.0
#         # },
#         # {
#         # "item_code": "apple-5",
#     	#  "qty": 16.0
#         # }
#         # ]
#         invoice_doc = frappe.get_doc({
#             "doctype":"Sales Invoice",
#             "customer":customer_name,
#             "pos_profile":pos_profile,
            
#             "is_pos":1,
#             "items":items,
#             "payments":[{
#             "mode_of_payment":"Cash",
#             "amount":paid_amount
#             }]
#         })
        
#         res_doc = invoice_doc.insert(ignore_permissions=True)
#         res_doc.submit()
#         return res_doc
#     except Exception as e:
#         return e
@frappe.whitelist()
def create_invoice(customer_name, paid_amount, items, user=None, is_pos=None, update_stock=None):
    import json

    # Parse items if necessary
    if isinstance(items, str):
        items = json.loads(items)

    # Get the current user
    current_user = frappe.session.user

    # Fetch User Permission records for 'Warehouse' allowed for the current user
    fallback_warehouse = frappe.get_all(
        'User Permission',
        filters={
            'user': current_user,
            'allow': 'Warehouse'
        },
        fields=['for_value']
    )

    # Determine the fallback warehouse value
    fallback_warehouse = fallback_warehouse[0]['for_value'] if fallback_warehouse else None

    if not fallback_warehouse:
        # Set a default warehouse if no user permissions are found
        fallback_warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse')
        if not fallback_warehouse:
            return {"error": "No warehouse assigned to user and no default warehouse found in Stock Settings."}

    pos_profile = None
    pos_warehouse = None

    # If user is provided and is_pos is enabled, fetch POS profile
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
            "update_stock": update_stock,  # Ensure update_stock is enabled
            "is_pos": is_pos,  # Use the value passed by the user
            "items": items,
        }

        # Include POS profile only if is_pos is enabled
        if is_pos:
            invoice_doc_data["pos_profile"] = pos_profile

            # Add payment details for POS invoices
            invoice_doc_data["payments"] = [{
                "mode_of_payment": "Cash",
                "amount": paid_amount
            }]

        invoice_doc = frappe.get_doc(invoice_doc_data)

        # Save and submit the document
        res_doc = invoice_doc.insert(ignore_permissions=True)
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