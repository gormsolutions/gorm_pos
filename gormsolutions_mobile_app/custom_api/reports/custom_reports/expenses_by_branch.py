import frappe
from frappe.utils import getdate

@frappe.whitelist()
def get_expenses_by_cost_center(from_date=None, to_date=None, cost_center=None, company=None, download=0):
    from_date = getdate(from_date) if from_date else None
    to_date = getdate(to_date) if to_date else None
    download = int(download or 0)

    # --- Journal Entries ---
    journal_expenses = frappe.db.sql("""
        SELECT je.name AS document,
               jea.account,
               jea.cost_center,
               je.company,
               jea.debit AS amount,
               je.posting_date
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE je.docstatus = 1
          AND je.is_opening != 1
          {posting_date_filter}
          {company_filter}
          {cost_center_filter}
        ORDER BY je.posting_date ASC
    """.format(
        posting_date_filter=f"AND je.posting_date >= '{from_date}'" if from_date else "",
        company_filter=f"AND je.company = '{company}'" if company else "",
        cost_center_filter=f"AND jea.cost_center = '{cost_center}'" if cost_center else ""
    ), as_dict=1)

    # --- Expense Claims ---
    expense_claims = frappe.db.sql("""
        SELECT ec.name AS document,
               ec.payable_account AS account,
               ecd.cost_center,
               ec.company,
               ecd.amount,
               ec.posting_date
        FROM `tabExpense Claim Detail` ecd
        JOIN `tabExpense Claim` ec ON ec.name = ecd.parent
        WHERE ec.docstatus = 1
          {posting_date_filter}
          {company_filter}
          {cost_center_filter}
        ORDER BY ec.posting_date ASC
    """.format(
        posting_date_filter=f"AND ec.posting_date >= '{from_date}'" if from_date else "",
        company_filter=f"AND ec.company = '{company}'" if company else "",
        cost_center_filter=f"AND ecd.cost_center = '{cost_center}'" if cost_center else ""
    ), as_dict=1)

    # Combine and label
    expenses = []
    for e in journal_expenses:
        expenses.append({
            "type": "Journal Entry",
            "document": e.document,
            "account": e.account,
            "cost_center": e.cost_center,
            "company": e.company,
            "amount": e.amount,
            "posting_date": e.posting_date
        })
    for e in expense_claims:
        expenses.append({
            "type": "Expense Claim",
            "document": e.document,
            "account": e.account,
            "cost_center": e.cost_center,
            "company": e.company,
            "amount": e.amount,
            "posting_date": e.posting_date
        })

    expenses.sort(key=lambda x: x["posting_date"])
    return expenses
