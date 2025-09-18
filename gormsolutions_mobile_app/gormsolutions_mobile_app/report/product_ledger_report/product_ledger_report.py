import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    filters.setdefault("item_code", None)
    filters.setdefault("warehouse", None)
    filters.setdefault("page", 0)
    filters.setdefault("page_len", 20)

    columns = [
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 180},
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": "Balance Qty", "fieldname": "qty_after_transaction", "fieldtype": "Float", "width": 120},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Posting Time", "fieldname": "posting_time", "fieldtype": "Time", "width": 80},
    ]

    query = """
        SELECT
            sle.item_code,
            sle.warehouse,
            sle.qty_after_transaction,
            sle.posting_date,
            sle.posting_time
        FROM `tabStock Ledger Entry` sle
        INNER JOIN (
            SELECT
                item_code,
                warehouse,
                MAX(CONCAT(posting_date, ' ', posting_time, ' ', creation)) AS latest_key
            FROM `tabStock Ledger Entry`
            WHERE is_cancelled = 1
              AND company = %(company)s
              AND posting_date BETWEEN %(start)s AND %(end)s
              AND (%(warehouse)s IS NULL OR warehouse = %(warehouse)s)
              AND (%(item_code)s IS NULL OR item_code = %(item_code)s)
            GROUP BY item_code, warehouse
        ) latest
        ON sle.item_code = latest.item_code
        AND sle.warehouse = latest.warehouse
        AND CONCAT(sle.posting_date, ' ', sle.posting_time, ' ', sle.creation) = latest.latest_key
        ORDER BY sle.item_code, sle.warehouse
        LIMIT %(page_len)s OFFSET %(offset)s
    """

    filters["offset"] = filters["page"] * filters["page_len"]

    data = frappe.db.sql(query, filters, as_dict=True)
    return columns, data
