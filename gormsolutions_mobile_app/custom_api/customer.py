import frappe
from frappe import _ # type: ignore

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
def create_customer(customer_name,mobile_no,location=None,email_id=None):

    doc = frappe.new_doc('Customer')
    doc.customer_name = customer_name
    doc.mobile_no = mobile_no
    doc.custom_location = location
    if email_id:
        doc.email_id = email_id
    doc.insert()

    return doc.name

@frappe.whitelist(allow_guest=True)
def create_customers(
    customer_name,
    mobile_no,
    email_id=None,
    naming_series="CUST-.YYYY.-",
    customer_type="Individual",
    customer_group=None,
    location=None,
    territory=None
):
    try:
        current_user = frappe.session.user

        # --- Step 1: Check for existing customer with same mobile number ---
        existing = frappe.db.get_all(
            "Customer",
            filters={"mobile_no": mobile_no.strip()},
            fields=["name", "customer_name"]
        )

        if existing:
            return {
                "status": "exists",
                "message": _("A customer with this mobile number already exists."),
                "customer": existing[0].name,
                "customer_name": existing[0].customer_name,
             }

        # --- Step 4: Create Customer ---
        doc = frappe.new_doc('Customer')
        doc.naming_series = naming_series
        doc.customer_name = customer_name.strip()
        doc.mobile_no = mobile_no.strip()
        doc.customer_type = customer_type
        doc.custom_location = location
        doc.customer_group = customer_group
        doc.territory = territory

        if email_id:
            doc.email_id = email_id.strip()

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Customer created successfully"),
            "customer": doc.name,
            "customer_name": doc.customer_name,
           }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Customer Creation Failed")
        return {
            "status": "error",
            "message": _("Failed to create customer"),
            "error": str(e)
        }

import frappe
from frappe import _

@frappe.whitelist()  # Allows this function to be called via API
def create_location(location_name, parent_location=None, company=None):
    """
    Create a new Location in ERPNext.
    
    Args:
        location_name (str): Name of the Location.
        parent_location (str, optional): Parent Location if any.
        company (str, optional): Company name if required (for some setups).

    Returns:
        dict: Success message with Location name or error.
    """
    try:
        # Check if location already exists
        existing = frappe.get_all('Location', filters={'location_name': location_name})
        if existing:
            return {'status': 'exists', 'message': f"Location '{location_name}' already exists."}

        # Create new Location
        location_doc = frappe.get_doc({
            'doctype': 'Location',
            'location_name': location_name,
            'parent_location': parent_location or '',
            'company': company or ''
        })
        location_doc.insert()
        frappe.db.commit()  # Save to database

        return {'status': 'success', 'message': f"Location '{location_name}' created.", 'name': location_doc.name}
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
