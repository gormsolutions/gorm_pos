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
    page_size=500,
    search_text=None
):
    """
    Stock Ledger Report with:
    - In/Out
    - Running balance
    - Opening balance
    - Pagination (cursor-based)
    - Search by item code or item name
    """

    filters = ["sle.is_cancelled = 0", "i.disabled = 0", "i.has_variants = 0", "i.is_stock_item = 1"]
    params = {"page_size": int(page_size)}

    # -------------------- filters --------------------
    if items:
        if isinstance(items, str):
            items = [x.strip() for x in items.split(",") if x.strip()]
        if items:  # only add filter if non-empty
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

    if search_text:
        filters.append("(sle.item_code LIKE %(search)s OR i.item_name LIKE %(search)s)")
        params["search"] = f"%{search_text}%"

    # -------------------- cursor --------------------
    if last_key:
        try:
            pd, pt, nm = last_key.split("|")
            params.update({"pd": pd, "pt": pt, "nm": nm})
            filters.append("(sle.posting_date, sle.posting_time, sle.name) > (%(pd)s, %(pt)s, %(nm)s)")
        except Exception:
            frappe.throw("Invalid cursor")

    where = " AND ".join(filters)

    # -------------------- opening balances --------------------
    opening_balances = {}
    if from_date:
        opening_sql = f"""
            SELECT sle.item_code, sle.warehouse, sle.qty_after_transaction AS opening_qty
            FROM `tabStock Ledger Entry` sle
            JOIN `tabItem` i ON i.name = sle.item_code
            WHERE sle.is_cancelled = 0 AND i.disabled = 0 AND i.has_variants = 0 AND i.is_stock_item = 1
              { 'AND sle.item_code IN %(items)s' if items else '' }
              { 'AND sle.company = %(company)s' if company else '' }
              { 'AND sle.warehouse = %(warehouse)s' if warehouse else '' }
              { 'AND i.item_group = %(item_group)s' if item_group else '' }
              { 'AND (sle.item_code LIKE %(search)s OR i.item_name LIKE %(search)s)' if search_text else '' }
              AND sle.posting_date < %(from_date)s
            ORDER BY sle.posting_date DESC, sle.posting_time DESC, sle.name DESC
        """
        rows_opening = frappe.db.sql(opening_sql, params, as_dict=True)
        seen = set()
        for r in rows_opening:
            key = f"{r.item_code}|{r.warehouse}"
            if key not in seen:
                opening_balances[key] = flt(r.opening_qty)
                seen.add(key)

    # -------------------- fetch stock ledger entries --------------------
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

    # -------------------- running balance --------------------
    balances = {}
    for r in rows:
        r["in_qty"] = flt(r["in_qty"])
        r["out_qty"] = flt(r["out_qty"])
        r["valuation_rate"] = flt(r["valuation_rate"])
        r["valuation_amount"] = flt(r["stock_value"])
        r["actual_qty"] = flt(r["actual_qty"])

        key = f"{r['item_code']}|{r['warehouse']}"
        opening = opening_balances.get(key, 0)
        prev_balance = balances.get(key, opening)
        r["running_balance"] = flt(r["qty_after_transaction"]) or prev_balance + r["actual_qty"]
        balances[key] = r["running_balance"]

    # -------------------- next key --------------------
    next_key = None
    if rows and len(rows) == page_size:
        last = rows[-1]
        next_key = f"{last.posting_date}|{last.posting_time}|{last.name}"

    return {
        "opening_balances": opening_balances,
        "data": rows,
        "next_key": next_key
    }
