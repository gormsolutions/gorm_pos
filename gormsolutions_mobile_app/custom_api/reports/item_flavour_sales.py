import frappe
from frappe import _

@frappe.whitelist()
def get_flavour_wise_sales(from_date, to_date, company=None, warehouse=None,
                           flavour=None, item_group=None, cost_center=None, customer=None,
                           invoice=None, start=0, page_length=50):
    """
    Flavour-wise sales summary with full filters for ERPNext-like report.
    Optional filter by Sales Invoice name.
    """
    conditions = [
        "c.docstatus = 1",
        "c.posting_date BETWEEN %(from_date)s AND %(to_date)s"
    ]
    params = {"from_date": from_date, "to_date": to_date}

    if company:
        conditions.append("c.company = %(company)s")
        params["company"] = company
    if warehouse:
        conditions.append("a.warehouse = %(warehouse)s")
        params["warehouse"] = warehouse
    if flavour:
        conditions.append("d.attribute_value = %(flavour)s")
        params["flavour"] = flavour
    if item_group:
        conditions.append("b.item_group = %(item_group)s")
        params["item_group"] = item_group
    if cost_center:
        conditions.append("c.cost_center = %(cost_center)s")
        params["cost_center"] = cost_center
    if customer:
        conditions.append("c.customer = %(customer)s")
        params["customer"] = customer
    if invoice:
        conditions.append("c.name = %(invoice)s")
        params["invoice"] = invoice

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            d.attribute_value AS flavour,
            SUM(a.qty) AS qty_sold,
            SUM(a.amount) AS amount,
            c.name AS invoice
        FROM `tabSales Invoice Item` a
        INNER JOIN `tabItem` b ON a.item_code = b.item_code
        INNER JOIN `tabSales Invoice` c ON c.name = a.parent
        INNER JOIN `tabItem Variant Attribute` d ON d.parent = b.name
            AND d.attribute = 'FLAVOUR'
        WHERE {where_clause}
        GROUP BY d.attribute_value, c.name
        ORDER BY d.attribute_value
        LIMIT %(start)s, %(page_length)s
    """

    return frappe.db.sql(
        query,
        {**params, "start": int(start), "page_length": int(page_length)},
        as_dict=True
    )

    

# file: gormsolutions_mobile_app/custom_api/reports/item_flavour_sales.py

@frappe.whitelist()
def get_flavour_values():
    """Return all FLAVOUR attribute values"""
    return frappe.db.get_all(
        "Item Attribute Value",
        filters={"parent": "FLAVOUR"},
        fields=["attribute_value"],
        order_by="attribute_value asc"
    )
