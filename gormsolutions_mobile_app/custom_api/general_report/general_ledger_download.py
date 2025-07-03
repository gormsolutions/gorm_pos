import frappe
import csv
from frappe.utils import get_site_path, nowdate

@frappe.whitelist()
def export_general_ledger(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    # Ensure filters is always a dict
    filters = filters or {}

    conditions = get_conditions(filters)

    query = f"""
        SELECT 
            posting_date, account, party_type, party, cost_center,
            debit, credit, voucher_type, voucher_no, against_voucher,
            account_currency, remarks, company
        FROM `tabGL Entry`
        WHERE {conditions}
        ORDER BY posting_date, creation
    """

    # Dynamic file name with today's date
    filename = f"gl_entry_dump_{nowdate()}.csv"
    file_path = get_site_path("public", "files", filename)

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write headers
        writer.writerow([
            "posting_date", "account", "party_type", "party", "cost_center",
            "debit", "credit", "voucher_type", "voucher_no", "against_voucher",
            "account_currency", "remarks", "company"
        ])

        # Paginate to avoid memory overload
        batch_size = 500000
        offset = 0
        total_rows = 0

        while True:
            batch_query = f"{query} LIMIT {batch_size} OFFSET {offset}"
            rows = frappe.db.sql(batch_query, filters, as_dict=True)
            if not rows:
                break

            for row in rows:
                writer.writerow([
                    row.get("posting_date"),
                    row.get("account"),
                    row.get("party_type"),
                    row.get("party"),
                    row.get("cost_center"),
                    row.get("debit"),
                    row.get("credit"),
                    row.get("voucher_type"),
                    row.get("voucher_no"),
                    row.get("against_voucher"),
                    row.get("account_currency"),
                    row.get("remarks"),
                    row.get("company")
                ])

            total_rows += len(rows)
            offset += batch_size

    # Log to server console
    frappe.logger().info(f"Exported {total_rows} GL Entry rows to {file_path}")

    # Return both file path and row count for progress tracking in JS
    return {
        "file_url": f"/files/{filename}",
        "rows_exported": total_rows
    }

def get_conditions(filters):
    conditions = "1=1"
    if filters.get("company"):
        conditions += " AND company = %(company)s"
    if filters.get("account"):
        conditions += " AND account = %(account)s"
    if filters.get("from_date"):
        conditions += " AND posting_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND posting_date <= %(to_date)s"
    return conditions
