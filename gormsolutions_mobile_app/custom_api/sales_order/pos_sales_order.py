import frappe
from frappe.utils import nowdate
from frappe import _

@frappe.whitelist()
def create_sales_order_from_pos(customer, items,date=None):
    """
    Create and submit a Sales Order from POS using user's POS Profile.

    Args:
        customer (str): Customer name
        items (list of dict): Each dict must include item_code, qty (and optionally delivery_date)

    Returns:
        str: Name of the created Sales Order
    """
    if not customer:
        frappe.throw(_("Customer is mandatory."))

    if not items or not isinstance(items, list):
        frappe.throw(_("Items are required and must be a list."))

    current_user = frappe.session.user

    # Fetch the default POS Profile for the user
    pos_profile_name = frappe.db.get_value("POS Profile User", {"default": 1, "user": current_user}, "parent")
    if not pos_profile_name:
        frappe.throw(_("No default POS Profile assigned to this user."))

    pos_profile = frappe.get_doc("POS Profile", pos_profile_name)

    source_warehouse = pos_profile.warehouse
    fulfillment_location = pos_profile.fulfillment_branch_
    originating_outlet = pos_profile.cost_center
    company = pos_profile.company
    cost_center = pos_profile.cost_center

    if not all([source_warehouse, fulfillment_location, originating_outlet, company]):
        frappe.throw(_("POS Profile is missing required fields: warehouse, fulfillment_branch_, cost_center, or company."))

    # Create Sales Order
    so = frappe.new_doc("Sales Order")
    so.customer = customer
    so.transaction_date = date or nowdate()
    so.company = company
    so.fulfillment_location = fulfillment_location
    so.originating_outlet = originating_outlet
    so.set_warehouse = source_warehouse
    so.pos_profile = pos_profile.name
    so.cost_center = cost_center

    for item in items:
        if not item.get("item_code") or not item.get("qty"):
            frappe.throw(_("Each item must have an Item Code and Quantity."))

        item_doc = frappe.get_doc("Item", item["item_code"])

        so.append("items", {
            "item_code": item["item_code"],
            "item_name": item_doc.item_name,
            "uom": item_doc.stock_uom,
            "qty": item["qty"],
            "delivery_date": item.get("delivery_date") or nowdate(),
            "warehouse": source_warehouse
        })

    so.insert()
    so.submit()

    return so.name

import frappe
from frappe import _
from frappe.utils import get_fullname

@frappe.whitelist()
def get_sales_orders_by_date(from_date, to_date):
    """
    Fetch Sales Orders between two dates with customer, status, cost center, item details,
    owner full name, and creation time.

    Args:
        from_date (str): Start date (YYYY-MM-DD)
        to_date (str): End date (YYYY-MM-DD)

    Returns:
        list: List of Sales Orders with items
    """

    if not from_date or not to_date:
        frappe.throw(_("Please provide both from_date and to_date."))

    current_user = frappe.session.user

    # Attempt to get permitted cost centers from POS Profiles
    pos_profiles = frappe.get_all(
        "POS Profile User",
        filters={"user": current_user},
        fields=["parent"]
    )

    permitted_cost_centers = []

    if pos_profiles:
        pos_profile_names = [p.parent for p in pos_profiles]
        cost_centers = frappe.get_all(
            "POS Profile",
            filters={"name": ["in", pos_profile_names]},
            fields=["cost_center"]
        )
        permitted_cost_centers = [c.cost_center for c in cost_centers if c.cost_center]

    # Base filters
    filters = {
        "transaction_date": ["between", [from_date, to_date]],
        "status": ["!=", "Cancelled"]
    }

    # Only apply cost center filter if available
    if permitted_cost_centers:
        filters["cost_center"] = ["in", permitted_cost_centers]

    # Fetch Sales Orders with owner and creation timestamp
    sales_orders = frappe.get_all(
        "Sales Order",
        filters=filters,
        fields=[
            "name",
            "customer",
            "transaction_date",
            "status",
            "cost_center",
            "owner",
            "grand_total",
            "creation"
        ],
        order_by="transaction_date desc"
    )

    # Append owner full name and items to each sales order
    for so in sales_orders:
        so["owner_full_name"] = get_fullname(so["owner"])
        so["creation_time"] = so["creation"].strftime('%Y-%m-%d %H:%M:%S')

        # Add items
        so["items"] = frappe.get_all(
            "Sales Order Item",
            filters={"parent": so["name"]},
            fields=[
                "item_code",
                "item_name",
                "qty",
                "uom",
                "warehouse",
                "rate",
                "amount",
                "delivery_date"
            ]
        )

    return sales_orders
