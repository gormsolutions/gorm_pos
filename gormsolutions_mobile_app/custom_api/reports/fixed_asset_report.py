import frappe
from frappe.utils import getdate, formatdate
from collections import defaultdict
from decimal import Decimal

@frappe.whitelist()
def get_fixed_asset_management_report(company=None, cost_center=None, from_date=None, to_date=None):
    """
    Fixed Asset Management Report.
    Includes:
      - Additions (purchases)
      - Depreciation
      - Disposals / retirements
      - Transfers between cost centers
      - Opening and closing balances
    Grouped by month and asset/account.
    """
    return _fetch_fixed_asset_report(company, cost_center, from_date, to_date)


def _fetch_fixed_asset_report(company, cost_center, from_date, to_date):
    values = {}
    conditions = ["gle.is_cancelled = 0"]

    if company:
        conditions.append("gle.company = %(company)s")
        values["company"] = company
    if cost_center:
        conditions.append("gle.cost_center = %(cost_center)s")
        values["cost_center"] = cost_center
    if from_date:
        conditions.append("gle.posting_date <= %(to_date)s")
        values["to_date"] = getdate(to_date) if to_date else frappe.utils.nowdate()

    condition_sql = " AND ".join(conditions)

    # Fetch GL entries for Fixed Assets and Depreciation
    gl_entries = frappe.db.sql(f"""
        SELECT
            DATE_FORMAT(gle.posting_date, '%%Y-%%m') AS month,
            gle.posting_date,
            gle.account,
            acc.account_type,
            acc.root_type,
            gle.cost_center,
            IFNULL(gle.debit, 0) AS debit,
            IFNULL(gle.credit, 0) AS credit,
            gle.remarks,
            gle.voucher_type,
            gle.voucher_no,
            gle.against,
            IFNULL(gle.party_type, '') AS party_type,
            IFNULL(gle.party, '') AS party
        FROM `tabGL Entry` gle
        LEFT JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE {condition_sql}
          AND acc.account_type IN ('Fixed Asset', 'Depreciation')
        ORDER BY gle.posting_date ASC
    """, values, as_dict=True)

    results = {}

    for row in gl_entries:
        month_key = row["month"]
        asset_key = row["account"]

        # Initialize month & asset
        if month_key not in results:
            results[month_key] = {}
        if asset_key not in results[month_key]:
            results[month_key][asset_key] = {
                "month": formatdate(month_key + "-01", "MMM YYYY"),
                "opening_balance": Decimal("0.0"),
                "additions": Decimal("0.0"),
                "depreciation": Decimal("0.0"),
                "disposals": Decimal("0.0"),
                "closing_balance": Decimal("0.0"),
                "entries": []
            }

        # Attach child items
        items = []
        if row["voucher_type"] in ["Purchase Invoice", "Purchase Receipt"]:
            table = "Purchase Invoice Item" if row["voucher_type"] == "Purchase Invoice" else "Purchase Receipt Item"
            items = frappe.db.sql(f"""
                SELECT item_code, item_name, description, qty, base_net_amount AS purchase_value
                FROM `tab{table}`
                WHERE parent = %s
            """, (row["voucher_no"]), as_dict=True)

            row_amount = sum([Decimal(i['purchase_value']) for i in items])
            results[month_key][asset_key]["additions"] += row_amount

        elif row["voucher_type"] == "Journal Entry":
            items = frappe.db.sql("""
                SELECT account AS item_code,
                    cost_center,
                    IFNULL(debit, 0) AS debit,
                    IFNULL(credit, 0) AS credit,
                    IFNULL(party_type, '') AS party_type,
                    IFNULL(party, '') AS party
                FROM `tabJournal Entry Account`
                WHERE parent = %s
            """, (row["voucher_no"]), as_dict=True)

            # classify child lines
            for i in items:
                debit_val = Decimal(i.get("debit", 0))
                credit_val = Decimal(i.get("credit", 0))

                # Determine whether this line is asset addition or depreciation
                child_account_type = frappe.db.get_value("Account", i.get("item_code"), "account_type")
                if child_account_type == "Fixed Asset":
                    results[month_key][asset_key]["additions"] += debit_val
                elif child_account_type == "Depreciation":
                    results[month_key][asset_key]["depreciation"] += credit_val
                # Optional: handle disposals if needed

        row["items"] = items
        results[month_key][asset_key]["entries"].append(row)

    # Compute opening/closing balances per asset/account
    final = []
    previous_month_balances = {}

    for month in sorted(results.keys()):
        for asset, data in results[month].items():
            # Opening balance = closing balance of previous month if exists
            data["opening_balance"] = previous_month_balances.get(asset, Decimal("0.0"))
            data["closing_balance"] = (
                data["opening_balance"] + data["additions"] - data["depreciation"] - data["disposals"]
            )
            previous_month_balances[asset] = data["closing_balance"]

            # Convert Decimal to float for JSON serialization
            final.append({
                "month": data["month"],
                "asset_account": asset,
                "opening_balance": float(data["opening_balance"]),
                "additions": float(data["additions"]),
                "depreciation": float(data["depreciation"]),
                "disposals": float(data["disposals"]),
                "closing_balance": float(data["closing_balance"]),
                "entries": data["entries"]
            })

    # Sort final report by month then asset
    final = sorted(final, key=lambda x: (x["month"], x["asset_account"]))
    return final
