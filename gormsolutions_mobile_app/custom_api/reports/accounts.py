import frappe
from frappe import _

@frappe.whitelist()
def get_bank_totals_grouped(from_date=None, to_date=None, owner=None):
    """
    Fetch total debit, credit and net balance
    grouped by selected accounts
    """

    accounts = [
        "1330 - MTN Mobile Money - SD",
        "1340 - Airtel Mobile Money - SD",
        "1350 - MOMO PAY - SD",
        "1210 - Centenary - SD",
        "1220 - Stanbic Bank - SD",
        "1310 - Cash accounts - SD",
        "1230 - Absa - SD",
        "DFCU Bank - SD"
    ]

    conditions = {
        "account": ["in", accounts],
        "is_cancelled": 0
    }

    if from_date and to_date:
        conditions["posting_date"] = ["between", [from_date, to_date]]

    if owner:
        conditions["owner"] = owner

    data = frappe.db.get_all(
        "GL Entry",
        filters=conditions,
        fields=[
            "account",
            "SUM(debit) as total_debit",
            "SUM(credit) as total_credit"
        ],
        group_by="account",
        order_by="account asc"
    )

    grand_debit = 0
    grand_credit = 0

    for row in data:
        row["total_debit"] = row.total_debit or 0
        row["total_credit"] = row.total_credit or 0
        row["net_balance"] = row["total_debit"] - row["total_credit"]

        grand_debit += row["total_debit"]
        grand_credit += row["total_credit"]

    return {
        "accounts": data,
        "grand_total_debit": grand_debit,
        "grand_total_credit": grand_credit,
        "grand_net_balance": grand_debit - grand_credit
    }
