import frappe, csv
from frappe.utils import get_site_path, nowdate, flt

@frappe.whitelist()
def export_stock_balance(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    filters = filters or {}

    # ------------------------------------------------------------------
    # 1.  Build WHERE clause identical to the standard report
    # ------------------------------------------------------------------
    conditions = ["1 = 1"]
    params = {}

    if filters.get("company"):
        conditions.append("wh.company = %(company)s")
        params["company"] = filters["company"]

    if filters.get("warehouse"):
        conditions.append("b.warehouse = %(warehouse)s")
        params["warehouse"] = filters["warehouse"]

    if filters.get("item_code"):
        conditions.append("b.item_code = %(item_code)s")
        params["item_code"] = filters["item_code"]

    if filters.get("item_group"):
        conditions.append("i.item_group = %(item_group)s")
        params["item_group"] = filters["item_group"]

    from_date = filters.get("from_date", "1900-01-01")
    to_date   = filters.get("to_date",   "2100-12-31")
    params.update({"from_date": from_date, "to_date": to_date})

    where_clause = " AND ".join(conditions)

    # ------------------------------------------------------------------
    # 2.  Single-row-per-Item-Warehouse query
    # ------------------------------------------------------------------
    sql = f"""
        SELECT
            b.item_code                                   AS item,
            i.item_name                                   AS item_name,
            i.item_group                                  AS item_group,
            b.warehouse                                   AS warehouse,
            i.stock_uom                                   AS stock_uom,

            COALESCE(b.actual_qty, 0)                     AS balance_qty,
            COALESCE(b.stock_value, 0)                    AS balance_value,

            COALESCE(op.opening_qty, 0)                   AS opening_qty,
            COALESCE(op.opening_value, 0)                 AS opening_value,

            COALESCE(io.in_qty, 0)                        AS in_qty,
            COALESCE(io.in_value, 0)                      AS in_value,
            COALESCE(io.out_qty, 0)                       AS out_qty,
            COALESCE(io.out_value, 0)                     AS out_value,

            COALESCE(b.valuation_rate, 0)                 AS valuation_rate,
            COALESCE(b.reserved_qty, 0)                   AS reserved_stock,
            wh.company                                    AS company
        FROM `tabBin` b
        INNER JOIN `tabItem`      i  ON i.name  = b.item_code
        INNER JOIN `tabWarehouse` wh ON wh.name = b.warehouse

        /* Opening balance before period */
        LEFT JOIN (
            SELECT
                item_code,
                warehouse,
                SUM(actual_qty)  AS opening_qty,
                SUM(stock_value) AS opening_value
            FROM   `tabStock Ledger Entry`
            WHERE  posting_date < %(from_date)s
            GROUP  BY item_code, warehouse
        ) op
            ON op.item_code = b.item_code
           AND op.warehouse = b.warehouse

        /* In / Out within the period */
        LEFT JOIN (
            SELECT
                item_code,
                warehouse,
                SUM(CASE WHEN actual_qty > 0 THEN actual_qty ELSE 0 END)  AS in_qty,
                SUM(CASE WHEN actual_qty > 0 THEN stock_value_difference ELSE 0 END) AS in_value,
                ABS(SUM(CASE WHEN actual_qty < 0 THEN actual_qty ELSE 0 END)) AS out_qty,
                ABS(SUM(CASE WHEN actual_qty < 0 THEN stock_value_difference ELSE 0 END)) AS out_value
            FROM   `tabStock Ledger Entry`
            WHERE  posting_date BETWEEN %(from_date)s AND %(to_date)s
            GROUP  BY item_code, warehouse
        ) io
            ON io.item_code = b.item_code
           AND io.warehouse = b.warehouse

        WHERE {where_clause}
        GROUP BY b.item_code, b.warehouse
        ORDER BY b.item_code, b.warehouse
    """

    rows = frappe.db.sql(sql, params, as_dict=True)

    # ------------------------------------------------------------------
    # 3.  Write CSV
    # ------------------------------------------------------------------
    filename = f"stock_balance_{nowdate()}.csv"
    file_path = get_site_path("public", "files", filename)

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Item", "Item Name", "Item Group", "Warehouse", "Stock UOM",
            "Balance Qty", "Balance Value", "Opening Qty", "Opening Value",
            "In Qty", "In Value", "Out Qty", "Out Value",
            "Valuation Rate", "Reserved Stock", "Company"
        ])
        for r in rows:
            writer.writerow([
                r.item, r.item_name, r.item_group, r.warehouse, r.stock_uom,
                flt(r.balance_qty), flt(r.balance_value),
                flt(r.opening_qty), flt(r.opening_value),
                flt(r.in_qty), flt(r.in_value),
                flt(r.out_qty), flt(r.out_value),
                flt(r.valuation_rate), flt(r.reserved_stock), r.company
            ])

    frappe.logger().info(f"Exported {len(rows)} rows to {file_path}")
    return {"file_url": f"/files/{filename}", "rows_exported": len(rows)}