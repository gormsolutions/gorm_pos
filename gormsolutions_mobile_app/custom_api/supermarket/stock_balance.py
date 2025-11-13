import frappe
from frappe import _

@frappe.whitelist()
def get_stock_balance(item_code=None, warehouse="Sal SuperMarket - HS", company="SalMart", start_date=None, end_date=None):
    """
    Fetch stock balance (qty + valuation rate) from Stock Ledger Entry.
    Supports optional item_code, warehouse, company, and date filters.
    """

    filters = {"warehouse": warehouse}
    if item_code:
        filters["item_code"] = item_code
    if company:
        filters["company"] = company

    sql = """
        SELECT 
            sle.item_code,
            sle.qty_after_transaction AS qty,
            sle.valuation_rate,
            sle.stock_value AS value,
            sle.posting_date
        FROM `tabStock Ledger Entry` sle
        WHERE sle.warehouse = %(warehouse)s
    """

    if item_code:
        sql += " AND sle.item_code = %(item_code)s"
    if company:
        sql += " AND sle.company = %(company)s"
    if start_date:
        sql += " AND sle.posting_date >= %(start_date)s"
    if end_date:
        sql += " AND sle.posting_date <= %(end_date)s"

    sql += " ORDER BY sle.posting_date DESC, sle.posting_time DESC, sle.creation DESC"

    sle = frappe.db.sql(sql, filters, as_dict=True)

    if not sle:
        if item_code:
            return [{
                "item_code": item_code,
                "qty": 0,
                "valuation_rate": 0,
                "value": 0
            }]
        else:
            return []

    # Get latest per item
    latest_per_item = {}
    for entry in sle:
        if entry["item_code"] not in latest_per_item:
            latest_per_item[entry["item_code"]] = entry

    return list(latest_per_item.values())

@frappe.whitelist()
def get_items_for_supermarkets():
    """Fetch all items under SuperMarkets"""
    return frappe.db.sql("""
        SELECT i.name as item_code, i.item_name
        FROM `tabItem` i
        JOIN `tabItem Group` ig ON i.item_group = ig.name
        WHERE ig.parent_item_group = 'SuperMarkets'
        ORDER BY i.item_name ASC
    """, as_dict=True)
