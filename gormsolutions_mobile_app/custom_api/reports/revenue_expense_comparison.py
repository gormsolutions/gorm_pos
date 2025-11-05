import frappe
from frappe.utils import getdate, flt, add_years

# -------------------------------
# Helper function (no import needed)
# -------------------------------
def get_expenses_by_cost_center(from_date=None, to_date=None, cost_center=None, company=None):
    from_date = getdate(from_date) if from_date else None
    to_date = getdate(to_date) if to_date else None

    # --- Journal Entries ---
    journal_expenses = frappe.db.sql(f"""
        SELECT jea.cost_center, jea.debit AS amount
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE je.docstatus = 1
          AND je.is_opening != 1
          {f"AND je.posting_date BETWEEN '{from_date}' AND '{to_date}'" if from_date and to_date else ""}
          {f"AND je.company = '{company}'" if company else ""}
          {f"AND jea.cost_center = '{cost_center}'" if cost_center else ""}
    """, as_dict=1)

    # --- Expense Claims ---
    expense_claims = frappe.db.sql(f"""
        SELECT ecd.cost_center, ecd.amount
        FROM `tabExpense Claim Detail` ecd
        JOIN `tabExpense Claim` ec ON ec.name = ecd.parent
        WHERE ec.docstatus = 1
          {f"AND ec.posting_date BETWEEN '{from_date}' AND '{to_date}'" if from_date and to_date else ""}
          {f"AND ec.company = '{company}'" if company else ""}
          {f"AND ecd.cost_center = '{cost_center}'" if cost_center else ""}
    """, as_dict=1)

    expenses = journal_expenses + expense_claims
    return expenses

# -------------------------------
# Main function
# -------------------------------
@frappe.whitelist()
def get_revenue_expense_comparison(from_date, to_date, company=None, cost_center=None):
    """
    Returns Revenue & Expense Comparison including SPLY.
    Only shows SPLY if there is actual data last year.
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    from_date_sply = add_years(from_date, -1)
    to_date_sply = add_years(to_date, -1)

    # Filters for Sales Invoice
    filters = ["si.docstatus = 1"]
    if company:
        filters.append(f"si.company = '{company}'")
    if cost_center:
        filters.append(f"si.cost_center = '{cost_center}'")

    where_clause = " AND ".join(filters)

    # Revenue - Current Period
    revenue = frappe.db.sql(f"""
        SELECT SUM(grand_total) AS total_revenue
        FROM `tabSales Invoice` si
        WHERE posting_date BETWEEN '{from_date}' AND '{to_date}'
        AND {where_clause}
    """, as_dict=1)[0].total_revenue or 0

    # Revenue - SPLY
    revenue_sply = frappe.db.sql(f"""
        SELECT SUM(grand_total) AS total_revenue
        FROM `tabSales Invoice` si
        WHERE posting_date BETWEEN '{from_date_sply}' AND '{to_date_sply}'
        AND {where_clause}
    """, as_dict=1)[0].total_revenue
    revenue_sply = flt(revenue_sply) if revenue_sply else None

    # Expenses - Current Period
    expenses = get_expenses_by_cost_center(from_date, to_date, cost_center, company)
    total_expense = sum([flt(e["amount"]) for e in expenses])

    # Expenses - SPLY
    expenses_sply = get_expenses_by_cost_center(from_date_sply, to_date_sply, cost_center, company)
    total_expense_sply = sum([flt(e["amount"]) for e in expenses_sply]) if expenses_sply else None

    return {
        "revenue": flt(revenue),
        "revenue_sply": revenue_sply,
        "expenses": flt(total_expense),
        "expenses_sply": total_expense_sply
    }
