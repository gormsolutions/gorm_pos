import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_stock_balances_cursor(item_group=None, warehouse=None, company=None, last_key=None, page_size=1000):
    conditions = []
    values = {}

    if item_group:
        conditions.append("i.item_group = %(item_group)s")
        values["item_group"] = item_group

    if warehouse:
        conditions.append("b.warehouse = %(warehouse)s")
        values["warehouse"] = warehouse

    if company:
        conditions.append("w.company = %(company)s")
        values["company"] = company

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = "WHERE " + where_clause

    query = f"""
        SELECT
            b.item_code,
            i.item_name,
            i.item_group,
            i.stock_uom,
            b.warehouse,
            b.actual_qty as balance_qty,
            b.valuation_rate,
            (b.actual_qty * b.valuation_rate) as valuation_amount
        FROM `tabBin` b
        JOIN `tabItem` i ON i.name = b.item_code
        JOIN `tabWarehouse` w ON w.name = b.warehouse
        {where_clause}
        ORDER BY b.item_code, b.warehouse
        LIMIT %(page_size)s
    """

    values["page_size"] = page_size
    data = frappe.db.sql(query, values, as_dict=True)

    return data

# import frappe

# import frappe
# from frappe.utils import flt, today


# @frappe.whitelist()
# def get_stock_balances_ledger(
#     company=None,
#     warehouse=None,
#     item_code=None,
#     item_name=None,
#     item_group=None,
#     from_date=None,
#     to_date=None,
#     last_key=None,
#     page_size=500
# ):
#     """
#     Return the latest stock balance per item per warehouse as of `to_date`,
#     filtered by optional parameters.
#     Supports pagination using `last_key` (item_code|warehouse) and `page_size`.
#     """
#     to_date = to_date or today()
#     from_date = from_date or '2000-01-01'
#     page_size = int(page_size)

#     # Base filters
#     conditions = ["i.disabled=0", "i.has_variants=0", "i.is_stock_item=1", "s.is_cancelled=0"]
#     values = {}

#     if company:
#         conditions.append("w.company=%(company)s")
#         values["company"] = company
#     if warehouse:
#         conditions.append("s.warehouse=%(warehouse)s")
#         values["warehouse"] = warehouse
#     if item_group:
#         conditions.append("i.item_group=%(item_group)s")
#         values["item_group"] = item_group
#     if item_code:
#         conditions.append("i.item_code=%(item_code)s")
#         values["item_code"] = item_code
#     if item_name:
#         conditions.append("i.item_name LIKE %(item_name)s")
#         values["item_name"] = f"%{item_name}%"

#     # Pagination using last_key
#     if last_key:
#         last_item, last_wh = last_key.split("|")
#         conditions.append("(s.item_code, s.warehouse) > (%(last_item)s, %(last_wh)s)")
#         values["last_item"] = last_item
#         values["last_wh"] = last_wh

#     where_clause = " AND ".join(conditions)

#     # Subquery: get the latest SLE per item per warehouse as of to_date
#     query = f"""
#         SELECT s.item_code, i.item_name, i.item_group, i.stock_uom,
#                s.warehouse, s.qty_after_transaction as balance_qty,
#                s.valuation_rate
#         FROM `tabStock Ledger Entry` s
#         JOIN `tabItem` i ON i.item_code = s.item_code
#         JOIN `tabWarehouse` w ON w.name = s.warehouse
#         WHERE s.posting_date <= %(to_date)s
#           AND {where_clause}
#           AND s.name IN (
#               SELECT MAX(s2.name)
#               FROM `tabStock Ledger Entry` s2
#               WHERE s2.posting_date <= %(to_date)s
#               GROUP BY s2.item_code, s2.warehouse
#           )
#         ORDER BY s.item_code, s.warehouse
#         LIMIT %(page_size)s
#     """

#     values["to_date"] = to_date
#     values["page_size"] = page_size

#     data = frappe.db.sql(query, values, as_dict=True)

#     # Add valuation_amount
#     results = []
#     for row in data:
#         row["valuation_amount"] = flt(row.balance_qty) * flt(row.valuation_rate)
#         results.append(row)

#     # Prepare next_key for pagination
#     next_key = None
#     if data:
#         last = data[-1]
#         next_key = f"{last.item_code}|{last.warehouse}"

#     return {"data": results, "next_key": next_key}

import frappe
from frappe.utils import flt, today

@frappe.whitelist()
def get_stock_balances_ledger(
    company=None,
    warehouse=None,
    item_code=None,
    item_name=None,
    item_group=None,
    from_date=None,
    to_date=None,
    last_key=None,
    page_size=500
):
    """
    Optimized: Return the latest stock balance per item per warehouse as of `to_date`,
    filtered by optional parameters. Supports pagination using last_key.
    """
    to_date = to_date or today()
    from_date = from_date or '2000-01-01'
    page_size = int(page_size)

    conditions = ["i.disabled=0", "i.has_variants=0", "i.is_stock_item=1", "s.is_cancelled=0"]
    values = {}

    if company:
        conditions.append("w.company=%(company)s")
        values["company"] = company
    if warehouse:
        conditions.append("s.warehouse=%(warehouse)s")
        values["warehouse"] = warehouse
    if item_group:
        conditions.append("i.item_group=%(item_group)s")
        values["item_group"] = item_group
    if item_code:
        conditions.append("i.item_code=%(item_code)s")
        values["item_code"] = item_code
    if item_name:
        conditions.append("i.item_name LIKE %(item_name)s")
        values["item_name"] = f"%{item_name}%"
    if last_key:
        last_item, last_wh = last_key.split("|")
        conditions.append("(s.item_code, s.warehouse) > (%(last_item)s, %(last_wh)s)")
        values["last_item"] = last_item
        values["last_wh"] = last_wh

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT item_code, item_name, item_group, stock_uom, warehouse,
               balance_qty, valuation_rate
        FROM (
            SELECT s.item_code, i.item_name, i.item_group, i.stock_uom, s.warehouse,
                   s.qty_after_transaction AS balance_qty, s.valuation_rate,
                   ROW_NUMBER() OVER (PARTITION BY s.item_code, s.warehouse ORDER BY s.posting_date DESC, s.posting_time DESC, s.name DESC) AS rn
            FROM `tabStock Ledger Entry` s
            JOIN `tabItem` i ON i.item_code = s.item_code
            JOIN `tabWarehouse` w ON w.name = s.warehouse
            WHERE s.posting_date <= %(to_date)s
            AND {where_clause}
        ) t
        WHERE rn = 1
        ORDER BY item_code, warehouse
        LIMIT %(page_size)s
    """

    values["to_date"] = to_date
    values["page_size"] = page_size

    data = frappe.db.sql(query, values, as_dict=True)

    results = []
    for row in data:
        row["valuation_amount"] = flt(row.balance_qty) * flt(row.valuation_rate)
        results.append(row)

    next_key = None
    if data:
        last = data[-1]
        next_key = f"{last.item_code}|{last.warehouse}"

    return {"data": results, "next_key": next_key}
