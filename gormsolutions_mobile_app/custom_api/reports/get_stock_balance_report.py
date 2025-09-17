# gormsolutions_mobile_app/custom_api/reports/get_stock_balance_report.py
import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_latest_stock_balances_pro(
    items=None,
    company=None,
    warehouse=None,
    item_group=None,
    from_date=None,
    to_date=None,
    last_key=None,          # cursor: "item_code|warehouse|posting_date|posting_time|name"
    page_size=200           # rows per request
):
    """
    Returns the latest stock balances per item & warehouse.
    Cursor-based pagination, zero balances skipped.
    Supports date range filtering.
    {
        data: [...],
        next_key: "item_code|warehouse|posting_date|posting_time|name"  # NULL when last page
    }
    """
    params = {"page_size": int(page_size)}
    filters = ["sle.is_cancelled = 0", "i.disabled = 0", "i.has_variants = 0"]

    # -------------------- filter builder --------------------
    if items:
        if isinstance(items, str):
            items = [x.strip() for x in items.split(",") if x.strip()]
        if items:
            filters.append("sle.item_code IN %(items)s")
            params["items"] = tuple(items)

    if company:
        filters.append("sle.company = %(company)s")
        params["company"] = company

    if warehouse:
        filters.append("sle.warehouse = %(warehouse)s")
        params["warehouse"] = warehouse

    if item_group:
        filters.append("i.item_group = %(item_group)s")
        params["item_group"] = item_group

    if from_date:
        filters.append("sle.posting_date >= %(from_date)s")
        params["from_date"] = from_date

    if to_date:
        filters.append("sle.posting_date <= %(to_date)s")
        params["to_date"] = to_date

    # -------------------- cursor --------------------
    if last_key:
        try:
            it, wh, pd, pt, nm = last_key.split("|")
            params.update({"it": it, "wh": wh, "pd": pd, "pt": pt, "nm": nm})
            filters.append(
                """(sle.item_code, sle.warehouse, sle.posting_date, sle.posting_time, sle.name) < 
                   (%(it)s, %(wh)s, %(pd)s, %(pt)s, %(nm)s)"""
            )
        except Exception:
            frappe.throw("Invalid cursor")

    where = " AND ".join(filters)

    # -------------------- latest stock per item/warehouse --------------------
    sql = f"""
        SELECT * FROM (
            SELECT
                sle.item_code,
                i.item_name,
                i.item_group,
                i.stock_uom,
                sle.warehouse,
                sle.qty_after_transaction AS balance_qty,
                sle.valuation_rate,
                sle.posting_date,
                sle.posting_time,
                sle.name,
                ROW_NUMBER() OVER (
                    PARTITION BY sle.item_code, sle.warehouse
                    ORDER BY sle.posting_date DESC,
                             sle.posting_time DESC,
                             sle.name DESC
                ) AS rn
            FROM `tabStock Ledger Entry` sle
            JOIN `tabItem` i ON i.name = sle.item_code
            WHERE {where}
              AND sle.qty_after_transaction != 0
        ) AS ranked
        WHERE rn = 1
        ORDER BY item_code ASC, warehouse ASC, posting_date ASC, posting_time ASC, name ASC
        LIMIT %(page_size)s
    """

    rows = frappe.db.sql(sql, params, as_dict=True)

    # -------------------- next cursor --------------------
    next_key = None
    if len(rows) == page_size:
        last = rows[-1]
        next_key = f"{last.item_code}|{last.warehouse}|{last.posting_date}|{last.posting_time}|{last.name}"

    # -------------------- normalize floats --------------------
    for r in rows:
        r["balance_qty"] = flt(r["balance_qty"])
        r["valuation_rate"] = flt(r["valuation_rate"])
        del r["name"]  # internal only

    return {"data": rows, "next_key": next_key}
