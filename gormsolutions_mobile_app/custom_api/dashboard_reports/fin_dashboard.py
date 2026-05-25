import frappe

@frappe.whitelist()
def chairman_dashboard(
    company=None,
    cost_center=None,
    item=None,
    item_group=None,
    warehouse=None,
    from_date=None,
    to_date=None
):

    # ---------------------------
    # 🔍 CONDITIONS
    # ---------------------------
    conditions = []
    values = {}

    def add_condition(field, key, value):
        conditions.append(f"{field} = %({key})s")
        values[key] = value

    if company:
        add_condition("sle.company", "company", company)

    if cost_center:
        add_condition("sle.cost_center", "cost_center", cost_center)

    if item:
        add_condition("sle.item_code", "item", item)

    if item_group:
        add_condition("i.item_group", "item_group", item_group)

    if warehouse:
        add_condition("sle.warehouse", "warehouse", warehouse)

    if from_date:
        conditions.append("sle.posting_date >= %(from_date)s")
        values["from_date"] = from_date

    if to_date:
        conditions.append("sle.posting_date <= %(to_date)s")
        values["to_date"] = to_date

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # ---------------------------
    # 📦 MAIN DATA
    # ---------------------------
    data = frappe.db.sql(f"""
        SELECT 
            sle.item_code,
            i.item_name,
            i.item_group,
            i.stock_uom,
            sle.warehouse,
            sle.valuation_rate,
            SUM(sle.actual_qty) AS qty,
            SUM(sle.actual_qty * sle.valuation_rate) AS stock_value
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabItem` i ON sle.item_code = i.name
        {where_clause}
        GROUP BY sle.item_code, i.item_name, i.item_group, sle.warehouse
    """, values, as_dict=True)

    # ---------------------------
    # 🔝 TOP 10 ITEMS (BY QTY)
    # ---------------------------
    top_items = sorted(data, key=lambda x: x.get("qty", 0), reverse=True)[:10]

    top_items_result = [
        {
            "item_code": d["item_code"],
            "item_name": d["item_name"],
            "qty": d.get("qty") or 0,
            "item_group": d["item_group"],
            "valuation_rate": d.get("valuation_rate") or 0,
            "uom": d.get("stock_uom"),
            "stock_value": d.get("stock_value") or 0
        }
        for d in top_items
    ]

    # ---------------------------
    # 💰 TOTAL STOCK VALUE
    # ---------------------------
    total_stock_value = sum(d.get("stock_value") or 0 for d in data)

    # ---------------------------
    # 📦 STOCK BY WAREHOUSE
    # ---------------------------
    warehouse_map = {}
    for d in data:
        wh = d["warehouse"]

        if wh not in warehouse_map:
            warehouse_map[wh] = {
                "qty": 0,
                "value": 0,
                "stock_uom": d.get("stock_uom")
            }

        warehouse_map[wh]["qty"] += d.get("qty") or 0
        warehouse_map[wh]["value"] += d.get("stock_value") or 0

    stock_by_warehouse = {
        "labels": list(warehouse_map.keys()),
        "qty": [v["qty"] for v in warehouse_map.values()],
        "value": [v["value"] for v in warehouse_map.values()],
        "valuation_rate": [
            (v["value"] / v["qty"]) if v["qty"] else 0
            for v in warehouse_map.values()
        ],
        "stock_uom": [v["stock_uom"] for v in warehouse_map.values()]
    }

    # ---------------------------
    # 📁 STOCK BY ITEM GROUP
    # ---------------------------
    group_map = {}
    for d in data:
        grp = d["item_group"]

        if grp not in group_map:
            group_map[grp] = {
                "qty": 0,
                "value": 0,
                "stock_uom": d.get("stock_uom")
            }

        group_map[grp]["qty"] += d.get("qty") or 0
        group_map[grp]["value"] += d.get("stock_value") or 0

    stock_by_item_group = {
        "labels": list(group_map.keys()),
        "qty": [v["qty"] for v in group_map.values()],
        "value": [v["value"] for v in group_map.values()],
        "valuation_rate": [
            (v["value"] / v["qty"]) if v["qty"] else 0
            for v in group_map.values()
        ],
        "stock_uom": [v["stock_uom"] for v in group_map.values()]
    }

    # ---------------------------
    # 🔐 RESPONSE
    # ---------------------------
    return {
        "top_10_items_by_spend": top_items_result,
        "total_stock_value": total_stock_value,
        "stock_by_warehouse": stock_by_warehouse,
        "stock_by_item_group": stock_by_item_group
    }