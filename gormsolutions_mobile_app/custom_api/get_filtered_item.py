import frappe
@frappe.whitelist()
def get_filtered_doctype():
    try:
        # Fetch the list of DocTypes filtered by name, ignoring permissions
        filtered_doctype = frappe.get_all(
            'DocType', 
            filters={'name': ['in', ['Supplier', 'Employee']]},
            fields=['name'],
            ignore_permissions=True  # This bypasses the permission check
        )
        return filtered_doctype
    except Exception as e:
        frappe.log_error(f"Error fetching filtered DocTypes: {e}")
        frappe.throw("Failed to fetch the filtered DocTypes. Please try again.")

