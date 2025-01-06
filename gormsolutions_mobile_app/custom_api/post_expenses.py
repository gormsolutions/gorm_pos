import frappe
from frappe import _

@frappe.whitelist()
def create_station_expenses(mode_of_payment, date, employee, items, station):
    # Get default account for mode of payment
    methods = frappe.get_value("Mode of Payment Account", {"parent": mode_of_payment}, "default_account")
    if not methods:
        frappe.throw(_("No default account found for the mode of payment: {0}").format(mode_of_payment))
    
    # Create new Journal Entry
    journal_entry = frappe.new_doc('Journal Entry')
    journal_entry.voucher_type = 'Journal Entry'
    journal_entry.company = 'Shell Elgon'
    journal_entry.posting_date = date
    journal_entry.custom_employee = employee
    
    for item in items:
        # Get default account for claim type
        claim_account = frappe.get_value("Expense Claim Account", {"parent": item['claim_type']}, "default_account")
        if not claim_account:
            frappe.throw(_("No default account found for the claim type: {0}").format(item['claim_type']))
        
        # Debit Entry
        journal_entry.append('accounts', {
            'account': "2110 - Creditors - SE",
            'party_type': item['party_type'],
            'party': item['party'],
            'description': item['description'],
            'debit_in_account_currency': item['amount'],
            'credit_in_account_currency': 0,
            'cost_center': station
        })
        
        # Credit Entry
        journal_entry.append('accounts', {
            'account': methods,
            'debit_in_account_currency': 0,
            'credit_in_account_currency': item['amount'],
            'cost_center': station
        })
        
        # Additional Debit Entry
        journal_entry.append('accounts', {
            'account': "2110 - Creditors - SE",
            'party_type': item['party_type'],
            'description': item['description'],
            'party': item['party'],
            'debit_in_account_currency': 0,
            'credit_in_account_currency': item['amount'],
            'cost_center': station
        })
        
        # Additional Credit Entry
        journal_entry.append('accounts', {
            'account': claim_account,
            'debit_in_account_currency': item['amount'],
            'credit_in_account_currency': 0,
            'cost_center': station
        })
    
    # Save the Journal Entry
    journal_entry.save()
    # Uncomment the next line if you want to submit the Journal Entry automatically
    journal_entry.submit()
    frappe.db.commit()
    frappe.msgprint(_(f"Successfully Posted Station Expenses for {employee}"))
