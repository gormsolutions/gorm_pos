import frappe

@frappe.whitelist(allow_guest=True)
def get_customer_details(limit,offset,search=None):
    if search:
        filters=[
        ['disabled','=','No'] ,
        ['customer_name','like','%'+search+'%']]
    else:
        filters=[
        ['disabled','=','No']]

    customer_details = frappe.db.get_list('Customer',
    filters = filters,
    fields=['name','customer_name', 'mobile_no','email_id'],
    
    start=offset,
    page_length=limit
    )

    return customer_details

@frappe.whitelist(allow_guest=True)
def create_customer(customer_name,mobile_no,email_id=None):

    doc = frappe.new_doc('Customer')
    doc.customer_name = customer_name
    doc.mobile_no = mobile_no
    if email_id:
        doc.email_id = email_id
    doc.insert()

    return doc.name