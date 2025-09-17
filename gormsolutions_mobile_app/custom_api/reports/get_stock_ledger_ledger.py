import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_stock_ledger_ledger(
    items=None,
    company=None,
    warehouse=None,
    item_group=None,
    from_date=None,
    to_date=None,
    last_key=None,
    page_size=200
):
    """
    Cursor-paginated stock ledger entries (non-cancelled, qty != 0)
    Adds: In Qty, Out Qty, Running Balance (from qty_after_transaction)
    Returns { data: [...], next_key: str }
    """
    params = {"page_size": int(page_size)}
    filters = ["sle.is_cancelled = 0"]

    # -------------------- filters --------------------
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
            pd, pt, nm = last_key.split("|")
            params.update({"pd": pd, "pt": pt, "nm": nm})
            filters.append(
                "(sle.posting_date, sle.posting_time, sle.name) > (%(pd)s, %(pt)s, %(nm)s)"
            )
        except Exception:
            frappe.throw("Invalid cursor")

    where = " AND ".join(filters)

    sql = f"""
        SELECT
            sle.name,
            sle.posting_date,
            sle.posting_time,
            sle.item_code,
            i.item_name,
            i.item_group,
            i.stock_uom,
            sle.warehouse,
            sle.actual_qty,
            sle.qty_after_transaction,
            sle.valuation_rate,
            sle.stock_value,
            sle.voucher_type,
            sle.voucher_no,
            CASE WHEN sle.actual_qty > 0 THEN sle.actual_qty ELSE 0 END AS in_qty,
            CASE WHEN sle.actual_qty < 0 THEN ABS(sle.actual_qty) ELSE 0 END AS out_qty
        FROM `tabStock Ledger Entry` sle
        JOIN `tabItem` i ON i.name = sle.item_code
        WHERE {where}
        ORDER BY sle.posting_date ASC, sle.posting_time ASC, sle.name ASC
        LIMIT %(page_size)s
    """

    rows = frappe.db.sql(sql, params, as_dict=True)

    # -------------------- pagination cursor --------------------
    next_key = None
    if len(rows) == page_size:
        last = rows[-1]
        next_key = f"{last.posting_date}|{last.posting_time}|{last.name}"

    # -------------------- normalize numeric fields --------------------
    for r in rows:
        r["actual_qty"] = flt(r["actual_qty"])
        r["qty_after_transaction"] = flt(r["qty_after_transaction"])  # running balance
        r["valuation_rate"] = flt(r["valuation_rate"])
        r["stock_value"] = flt(r["stock_value"])
        r["in_qty"] = flt(r["in_qty"])
        r["out_qty"] = flt(r["out_qty"])
        r["running_balance"] = r["qty_after_transaction"]  # directly from ERPNext

    return {"data": rows, "next_key": next_key}
