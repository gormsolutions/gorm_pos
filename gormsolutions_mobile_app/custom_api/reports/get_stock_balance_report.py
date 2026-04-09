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
    last_key=None,   # cursor: "item_code|warehouse"
    page_size=200
    ):
    """
    Returns latest stock balances per stock item & warehouse.
    Shows only stock items with balance_qty != 0.
    from_date/to_date filter transactions for valuation_rate calculation. 
    """
    params = {"page_size": int(page_size)}
    item_filters = ["i.disabled = 0", "i.has_variants = 0", "i.is_stock_item = 1"]

    if items:
        if isinstance(items, str):
            items = [x.strip() for x in items.split(",") if x.strip()]
        if items:
            item_filters.append("i.name IN %(items)s")
            params["items"] = tuple(items)

    if item_group:
        item_filters.append("i.item_group = %(item_group)s")
        params["item_group"] = item_group

    where_item = " AND ".join(item_filters)

    # -------------------- cursor --------------------
    cursor_filter = ""
    if last_key:
        try:
            it, wh = last_key.split("|")
            params.update({"it": it, "wh": wh})
            cursor_filter = f"AND (i.name, sle.warehouse) > (%(it)s, %(wh)s)"
        except Exception:
            frappe.throw("Invalid cursor")

    # -------------------- SLE filter for valuation_rate --------------------
    sle_filters = ["sle.is_cancelled = 0"]
    if company:
        sle_filters.append("sle.company = %(company)s")
        params["company"] = company
    if warehouse:
        sle_filters.append("sle.warehouse = %(warehouse)s")
        params["warehouse"] = warehouse
    if from_date:
        sle_filters.append("sle.posting_date >= %(from_date)s")
        params["from_date"] = from_date
    if to_date:
        sle_filters.append("sle.posting_date <= %(to_date)s")
        params["to_date"] = to_date

    sle_where_sql = f"AND ({' AND '.join(sle_filters)})" if sle_filters else ""

    # -------------------- SQL --------------------
    sql = f"""
        SELECT *
        FROM (
            SELECT
                i.name AS item_code,
                i.item_name,
                i.item_group,
                i.stock_uom,
                sle.warehouse,
                sle.qty_after_transaction AS balance_qty,
                sle.valuation_rate,
                ROW_NUMBER() OVER (
                    PARTITION BY i.name, sle.warehouse
                    ORDER BY sle.posting_date DESC,
                             sle.posting_time DESC,
                             sle.name DESC
                ) AS rn
            FROM `tabItem` i
            LEFT JOIN `tabStock Ledger Entry` sle
                ON i.name = sle.item_code
                {sle_where_sql}
            WHERE {where_item}
        ) AS ranked
        WHERE rn = 1
          AND balance_qty <> 0
        {cursor_filter}
        ORDER BY item_code ASC, warehouse ASC
        LIMIT %(page_size)s
    """

    rows = frappe.db.sql(sql, params, as_dict=True)

    # -------------------- next cursor --------------------
    next_key = None
    if len(rows) == page_size:
        last = rows[-1]
        next_key = f"{last.item_code}|{last.warehouse}"

    # --------------------normalize floats & defaults --------------------
    for r in rows:
        r["balance_qty"] = flt(r.get("balance_qty", 0))
        r["valuation_rate"] = flt(r.get("valuation_rate", 0))
        if not r.get("warehouse"):
            r["warehouse"] = "No Warehouse"

    return {"data": rows, "next_key": next_key}
