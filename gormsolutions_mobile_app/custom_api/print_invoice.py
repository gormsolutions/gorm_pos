import frappe

@frappe.whitelist(allow_guest=True)
def print_invoice(invoice_id):
    res_doc = frappe.get_doc("Sales Invoice",invoice_id)
    print_format = frappe.render_template("gormsolutions_mobile_app/templates/print_format/pos_invoice.html",{'doc':res_doc},is_path = True)
    return print_format