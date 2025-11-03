import frappe
import json
from datetime import datetime, timedelta
import calendar

@frappe.whitelist()
def get_budget_vs_actual_expenses(filters):
    """
    Returns Budget vs Actual Expenses report data including Expense Claims and Journal Entries.
    Filters expected as JSON string or dict:
        - from_date
        - to_date
        - company
        - cost_center (optional)
        - account (optional)
        - period: Daily / Weekly / Monthly / Quarterly / Yearly
    """
    # Parse JSON filters if needed
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = {}

    f = frappe._dict(filters or {})
    period = f.get("period") or "Monthly"

    # Determine budget year from from_date
    budget_year = datetime.strptime(f.get("from_date"), "%Y-%m-%d").year if f.get("from_date") else None

    # 🔹 Build WHERE clause dynamically for Expense Claim
    conditions = ["ec.docstatus = 1"]
    if f.get("company"):
        conditions.append("ec.company = %(company)s")
    if f.get("from_date") and f.get("to_date"):
        conditions.append("ec.posting_date BETWEEN %(from_date)s AND %(to_date)s")
    if f.get("cost_center"):
        conditions.append("ed.cost_center = %(cost_center)s")
    if f.get("account"):
        conditions.append("ed.default_account = %(account)s")
    where_clause = "WHERE " + " AND ".join(conditions)

    # 🔹 Expense Claim Data
    expense_claim_query = f"""
        SELECT
            CASE
                WHEN %(period)s='Daily' THEN DATE_FORMAT(ec.posting_date, '%%Y-%%m-%%d')
                WHEN %(period)s='Weekly' THEN CONCAT(YEAR(ec.posting_date), '-W', LPAD(WEEK(ec.posting_date,1),2,'0'))
                WHEN %(period)s='Monthly' THEN DATE_FORMAT(ec.posting_date, '%%Y-%%m')
                WHEN %(period)s='Quarterly' THEN CONCAT(YEAR(ec.posting_date), '-Q', QUARTER(ec.posting_date))
                WHEN %(period)s='Yearly' THEN DATE_FORMAT(ec.posting_date, '%%Y')
            END AS period_label,
            ed.cost_center AS cost_center,
            ed.default_account AS account,
            SUM(ed.amount) AS actual_expense
        FROM `tabExpense Claim` ec
        JOIN `tabExpense Claim Detail` ed ON ed.parent = ec.name AND ed.parenttype='Expense Claim'
        {where_clause}
        GROUP BY period_label, ed.cost_center, ed.default_account
    """
    expense_claim_data = frappe.db.sql(expense_claim_query, f, as_dict=True)

    # 🔹 Journal Entry Data
    conditions_je = ["je.docstatus = 1", "jec.debit > 0"]
    if f.get("company"):
        conditions_je.append("je.company = %(company)s")
    if f.get("from_date") and f.get("to_date"):
        conditions_je.append("je.posting_date BETWEEN %(from_date)s AND %(to_date)s")
    if f.get("cost_center"):
        conditions_je.append("jec.cost_center = %(cost_center)s")
    if f.get("account"):
        conditions_je.append("jec.account = %(account)s")
    where_clause_je = "WHERE " + " AND ".join(conditions_je)

    journal_entry_query = f"""
        SELECT
            CASE
                WHEN %(period)s='Daily' THEN DATE_FORMAT(je.posting_date, '%%Y-%%m-%%d')
                WHEN %(period)s='Weekly' THEN CONCAT(YEAR(je.posting_date), '-W', LPAD(WEEK(je.posting_date,1),2,'0'))
                WHEN %(period)s='Monthly' THEN DATE_FORMAT(je.posting_date, '%%Y-%%m')
                WHEN %(period)s='Quarterly' THEN CONCAT(YEAR(je.posting_date), '-Q', QUARTER(je.posting_date))
                WHEN %(period)s='Yearly' THEN DATE_FORMAT(je.posting_date, '%%Y')
            END AS period_label,
            jec.cost_center AS cost_center,
            jec.account AS account,
            SUM(jec.debit) AS actual_expense
        FROM `tabJournal Entry` je
        JOIN `tabJournal Entry Account` jec ON je.name = jec.parent
        {where_clause_je}
        GROUP BY period_label, jec.cost_center, jec.account
    """
    journal_entry_data = frappe.db.sql(journal_entry_query, f, as_dict=True)

    # 🔹 Combine Expense Claim & Journal Entry
    combined = {}
    for row in expense_claim_data + journal_entry_data:
        key = (row['period_label'], row['cost_center'], row['account'])
        if key in combined:
            combined[key]['actual_expense'] += row['actual_expense']
        else:
            combined[key] = row

    data = list(combined.values())

    # 🔹 Compute Budget, SPLY, Achievement, Growth
    for d in data:
        # Budget filtered by cost center, account, and year
        budget = frappe.db.sql("""
            SELECT SUM(ba.budget_amount)
            FROM `tabBudget` b
            JOIN `tabBudget Account` ba ON ba.parent = b.name
            WHERE b.company = %(company)s
              AND b.cost_center = %(cost_center)s
              AND ba.account = %(account)s
              AND b.fiscal_year = %(budget_year)s
        """, {
            "company": f.get("company"),
            "cost_center": d.cost_center,
            "account": d.account,
            "budget_year": budget_year
        })[0][0] or 0
        d.budget = budget

        # SPLY calculation (last year same period)
        sply_start, sply_end = None, None
        try:
            if period == "Daily":
                sply_start = sply_end = datetime.strptime(d.period_label, "%Y-%m-%d") - timedelta(days=365)
            elif period == "Weekly":
                year, week = map(int, d.period_label.split("-W"))
                sply_start = datetime.fromisocalendar(year-1, week, 1)
                sply_end = datetime.fromisocalendar(year-1, week, 7)
            elif period == "Monthly":
                y, m = map(int, d.period_label.split("-"))
                sply_start = datetime(y-1, m, 1)
                sply_end = datetime(y-1, m, calendar.monthrange(y-1, m)[1])
            elif period == "Quarterly":
                y, q = d.period_label.split("-Q")
                y, q = int(y)-1, int(q)
                start_month = 3*(q-1)+1
                end_month = start_month+2
                sply_start = datetime(y, start_month, 1)
                sply_end = datetime(y, end_month, calendar.monthrange(y, end_month)[1])
            elif period == "Yearly":
                y = int(d.period_label)-1
                sply_start = datetime(y, 1, 1)
                sply_end = datetime(y, 12, 31)
        except Exception:
            sply_start = sply_end = None

        if sply_start and sply_end:
            sply_expense_claim = frappe.db.sql("""
                SELECT SUM(ed.amount)
                FROM `tabExpense Claim` ec
                JOIN `tabExpense Claim Detail` ed ON ed.parent = ec.name AND ed.parenttype='Expense Claim'
                WHERE ec.company=%(company)s
                  AND ed.cost_center=%(cost_center)s
                  AND ed.default_account=%(account)s
                  AND ec.posting_date BETWEEN %(start)s AND %(end)s
                  AND ec.docstatus = 1
            """, {
                "company": f.get("company"),
                "cost_center": d.cost_center,
                "account": d.account,
                "start": sply_start,
                "end": sply_end
            })[0][0] or 0

            sply_journal_entry = frappe.db.sql("""
                SELECT SUM(jec.debit)
                FROM `tabJournal Entry` je
                JOIN `tabJournal Entry Account` jec ON je.name = jec.parent
                WHERE je.company=%(company)s
                  AND jec.cost_center=%(cost_center)s
                  AND jec.account=%(account)s
                  AND je.posting_date BETWEEN %(start)s AND %(end)s
                  AND je.docstatus = 1
            """, {
                "company": f.get("company"),
                "cost_center": d.cost_center,
                "account": d.account,
                "start": sply_start,
                "end": sply_end
            })[0][0] or 0

            d.sply = sply_expense_claim + sply_journal_entry
        else:
            d.sply = 0

        d.achievement = (d.actual_expense / d.budget * 100) if d.budget else 0
        d.growth = ((d.actual_expense - d.sply) / d.sply * 100) if d.sply else 0

    return data
