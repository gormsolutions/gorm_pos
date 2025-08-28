import frappe
import csv
from frappe.utils import get_site_path, nowdate

@frappe.whitelist()
def export_stock_ledger(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    filters = filters or {}

    conditions, extra_joins = get_stock_conditions(filters)

    query = f"""
        SELECT
            sle.posting_date,
            sle.posting_time,
            sle.item_code,
            sle.warehouse,
            sle.actual_qty,
            sle.qty_after_transaction,
            sle.incoming_rate,
            sle.valuation_rate,
            sle.stock_value,
            sle.stock_value_difference,
            sle.voucher_type,
            sle.voucher_no,
            sle.batch_no,
            sle.serial_no,
            sle.company,
            sle.project,
            sle.stock_uom
        FROM `tabStock Ledger Entry` sle
        {extra_joins}
        WHERE {conditions}
        ORDER BY sle.posting_date, sle.posting_time, sle.creation
    """

    filename = f"stock_ledger_dump_{nowdate()}.csv"
    file_path = get_site_path("public", "files", filename)

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            "posting_date", "posting_time", "item_code", "warehouse",
            "actual_qty", "qty_after_transaction", "incoming_rate",
            "valuation_rate", "stock_value", "stock_value_difference",
            "voucher_type", "voucher_no", "batch_no", "serial_no",
            "company", "project", "stock_uom"
        ])

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
                    row.posting_date,
                    row.posting_time,
                    row.item_code,
                    row.warehouse,
                    row.actual_qty,
                    row.qty_after_transaction,
                    row.incoming_rate,
                    row.valuation_rate,
                    row.stock_value,
                    row.stock_value_difference,
                    row.voucher_type,
                    row.voucher_no,
                    row.batch_no,
                    row.serial_no,
                    row.company,
                    row.project,
                    row.stock_uom
                ])

            total_rows += len(rows)
            offset += batch_size

    frappe.logger().info(f"Exported {total_rows} Stock Ledger rows to {file_path}")

    return {
        "file_url": f"/files/{filename}",
        "rows_exported": total_rows
    }


def get_stock_conditions(filters):
    """
    Build WHERE clause + optional JOIN for item_group filtering.
    Returns (where_clause_string, join_clause_string)
    """
    conditions = ["1=1"]
    joins = []

    # Direct fields
    if filters.get("item_code"):
        conditions.append("sle.item_code = %(item_code)s")
    if filters.get("warehouse"):
        conditions.append("sle.warehouse = %(warehouse)s")
    if filters.get("company"):
        conditions.append("sle.company = %(company)s")
    if filters.get("voucher_no"):
        conditions.append("sle.voucher_no = %(voucher_no)s")
    if filters.get("batch_no"):
        conditions.append("sle.batch_no = %(batch_no)s")
    if filters.get("from_date"):
        conditions.append("sle.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("sle.posting_date <= %(to_date)s")

    # Item group (via Item master)
    if filters.get("item_group"):
        joins.append(
            "INNER JOIN `tabItem` item ON item.name = sle.item_code"
        )
        conditions.append("item.item_group = %(item_group)s")

    return " AND ".join(conditions), " ".join(joins)