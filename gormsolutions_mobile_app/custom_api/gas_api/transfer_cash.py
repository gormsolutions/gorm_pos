import frappe
from frappe import _

@frappe.whitelist()
def create_cash_transfer(
    posting_date,
    account_paid_to,
    reference_no,
    reference_date,
    paid_amount
 ):
    # Validate that accounts are different
    user = frappe.session.user
    expense_setting = frappe.get_doc("Expense Settings", {"user": user})
    if expense_setting.account_paid_from == account_paid_to:
        frappe.throw(_("Account Paid From and Account Paid To must be different"))
        
   
    
    if not expense_setting:
        frappe.throw(_("Expense settings not found for the user."))

    # Create a Payment Entry document
    payment_entry = frappe.new_doc("Payment Entry")
    payment_entry.payment_type = "Internal Transfer"
    payment_entry.posting_date = posting_date
    payment_entry.cost_center = expense_setting.cost_center
    payment_entry.paid_from = expense_setting.account_paid_from 
    payment_entry.paid_to = account_paid_to
    payment_entry.reference_no = reference_no
    payment_entry.reference_date = reference_date
    payment_entry.paid_amount = paid_amount
    payment_entry.received_amount = paid_amount
    payment_entry.custom_employee = expense_setting.party

    payment_entry.insert()
    payment_entry.submit()

    frappe.msgprint(_(f"Cash Transfer {payment_entry.name} created successfully."))

    return {
        "status": "success",
        "payment_entry": payment_entry.name
    }
