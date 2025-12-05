import frappe
from frappe.utils import getdate

# @frappe.whitelist()
# def get_expenses_by_cost_center(from_date=None, to_date=None, cost_center=None, company=None, download=0):
#     from_date = getdate(from_date) if from_date else None
#     to_date = getdate(to_date) if to_date else None
#     download = int(download or 0)

#     # --- Journal Entries ---
#     journal_expenses = frappe.db.sql("""
#         SELECT je.name AS document,
#                jea.account,
#                jea.cost_center,
#                je.company,
#                jea.debit AS amount,
#                je.posting_date
#         FROM `tabJournal Entry Account` jea
#         JOIN `tabJournal Entry` je ON je.name = jea.parent
#         WHERE je.docstatus = 1
#           AND je.is_opening != 1
#           {posting_date_filter}
#           {company_filter}
#           {cost_center_filter}
#         ORDER BY je.posting_date ASC
#     """.format(
#         posting_date_filter=f"AND je.posting_date >= '{from_date}'" if from_date else "",
#         company_filter=f"AND je.company = '{company}'" if company else "",
#         cost_center_filter=f"AND jea.cost_center = '{cost_center}'" if cost_center else ""
#     ), as_dict=1)

#     # --- Expense Claims ---
#     expense_claims = frappe.db.sql("""
#         SELECT ec.name AS document,
#                ec.payable_account AS account,
#                ecd.cost_center,
#                ec.company,
#                ecd.amount,
#                ec.posting_date
#         FROM `tabExpense Claim Detail` ecd
#         JOIN `tabExpense Claim` ec ON ec.name = ecd.parent
#         WHERE ec.docstatus = 1
#           {posting_date_filter}
#           {company_filter}
#           {cost_center_filter}
#         ORDER BY ec.posting_date ASC
#     """.format(
#         posting_date_filter=f"AND ec.posting_date >= '{from_date}'" if from_date else "",
#         company_filter=f"AND ec.company = '{company}'" if company else "",
#         cost_center_filter=f"AND ecd.cost_center = '{cost_center}'" if cost_center else ""
#     ), as_dict=1)

#     # Combine and label
#     expenses = []
#     for e in journal_expenses:
#         expenses.append({
#             "type": "Journal Entry",
#             "document": e.document,
#             "account": e.account,
#             "cost_center": e.cost_center,
#             "company": e.company,
#             "amount": e.amount,
#             "posting_date": e.posting_date
#         })
#     for e in expense_claims:
#         expenses.append({
#             "type": "Expense Claim",
#             "document": e.document,
#             "account": e.account,
#             "cost_center": e.cost_center,
#             "company": e.company,
#             "amount": e.amount,
#             "posting_date": e.posting_date
#         })

#     expenses.sort(key=lambda x: x["posting_date"])
#     return expenses


import frappe
from frappe.utils import getdate

@frappe.whitelist()
def get_expenses_pnl_style(from_date=None, to_date=None, cost_center=None, company=None):
    from_date = getdate(from_date) if from_date else None
    to_date = getdate(to_date) if to_date else None

    # Step 1: Get all accounts to exclude (parent + children)
    excluded_parent = "5110000 - Stock Expenses - DC"
    excluded_accounts = ["30000 - COGS - DIRECT BY PRODUCT - DC", excluded_parent]

    # Include all children of excluded parent
    children = frappe.get_all("Account", filters={"parent_account": excluded_parent}, pluck="name")
    excluded_accounts.extend(children)

    # Step 2: Build conditions
    conditions = ["gle.is_cancelled = 0", "acc.root_type = 'Expense'"]
    if excluded_accounts:
        conditions.append("acc.name NOT IN ({})".format(", ".join(["%s"]*len(excluded_accounts))))

    values = excluded_accounts.copy()

    if from_date:
        conditions.append("gle.posting_date >= %s")
        values.append(from_date)
    if to_date:
        conditions.append("gle.posting_date <= %s")
        values.append(to_date)
    if company:
        conditions.append("gle.company = %s")
        values.append(company)
    if cost_center:
        conditions.append("gle.cost_center = %s")
        values.append(cost_center)

    condition_str = " AND ".join(conditions)

    # Step 3: Fetch accounts with totals
    query = f"""
        SELECT
            acc.name AS account,
            acc.account_name,
            acc.parent_account,
            acc.is_group,
            SUM(gle.debit - gle.credit) AS amount
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE {condition_str}
        GROUP BY acc.name, acc.account_name, acc.parent_account, acc.is_group
        ORDER BY acc.account_name
    """

    data = frappe.db.sql(query, values, as_dict=True)

    # Step 4: Build tree structure
    account_map = {d['account']: {**d, 'children': []} for d in data}
    roots = []

    for d in data:
        parent = d.get('parent_account')
        if parent and parent in account_map:
            account_map[parent]['children'].append(account_map[d['account']])
        else:
            roots.append(account_map[d['account']])

    def compute_totals(node):
        if node['children']:
            node['amount'] = sum([compute_totals(c) for c in node['children']])
        return node['amount']

    for r in roots:
        compute_totals(r)

    # Step 5: Flatten tree for front-end
    def flatten(node, level=0, res=[]):
        res.append({
            'account': node['account'],
            'account_name': node['account_name'],
            'parent_account': node['parent_account'],
            'is_group': node['is_group'],
            'amount': node['amount'],
            'level': level
        })
        for c in node['children']:
            flatten(c, level+1, res)
        return res

    flat_result = []
    for r in roots:
        flatten(r, 0, flat_result)

    # Step 6: Remove zero-amount accounts
    return [d for d in flat_result if d['amount'] != 0]
