import frappe
from frappe.utils import nowdate, add_days
import csv, io, json

@frappe.whitelist()
def get_material_transfer_report(filters=None, download=False):
    """
    Fetch Material Transfer Stock Entries with filters including additional child table fields:
    Accepted Qty, Original Qty, Difference Qty, and Item Code
    """

    # Convert filters from JSON string to dict if needed
    if filters:
        if isinstance(filters, str):
            filters = json.loads(filters)
    else:
        filters = {}

    # Default date filter: last 90 days
    from_date = filters.get("from_date") or add_days(nowdate(), -90)
    to_date = filters.get("to_date") or nowdate()

    # Step 1: Fetch Stock Entries
    se_filters = {
        "stock_entry_type": "Material Transfer",
        "modified": ["between", [from_date, to_date]]
    }

    if filters.get("company"):
        se_filters["company"] = filters["company"]

    if filters.get("source_warehouse"):
        se_filters["from_warehouse"] = filters["source_warehouse"]

    if filters.get("target_warehouse"):
        se_filters["to_warehouse"] = filters["target_warehouse"]

    if filters.get("ID"):  # filter by Stock Entry ID
        se_filters["name"] = filters["ID"]

    stock_entries = frappe.get_all(
        "Stock Entry",
        filters=se_filters,
        fields=["name", "docstatus", "stock_entry_type", "from_warehouse", "to_warehouse", "posting_date","posting_time","company"],
        order_by="modified desc",
        limit_page_length=5000
    )

    if not stock_entries:
        return []

    entry_names = [se.name for se in stock_entries]

    # Step 2: Fetch child table items in bulk
    item_filters = {"parent": ["in", entry_names]}

    if filters.get("item_name"):
        item_filters["item_name"] = filters["item_name"]

    if filters.get("item_code"):
        item_filters["item_code"] = filters["item_code"]

    if filters.get("cost_center"):
        item_filters["cost_center"] = filters["cost_center"]

    items = frappe.get_all(
        "Stock Entry Detail",
        filters=item_filters,
        fields=[
            "parent",
            "item_code",            # <-- new
            "item_name",
            "qty",                  # Stock Qty
            "cost_center",
            "custom_accepted_qty",  # Accepted Qty
            "custom_original_qty",  # Original Qty
            "custom_difference_qty" # Difference Qty
        ],
        order_by="parent"
    )

    # Step 3: Map items to their Stock Entry
    se_items_map = {}
    for item in items:
        se_items_map.setdefault(item.parent, []).append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "cost_center": item.cost_center,
            "custom_accepted_qty": item.get("custom_accepted_qty"),
            "custom_original_qty": item.get("custom_original_qty"),
            "custom_difference_qty": item.get("custom_difference_qty")
        })

    # Step 4: Prepare report
    report = []
    for se in stock_entries:
        for item in se_items_map.get(se.name, []):
            report.append({
                "ID": se.name,
                "Status": se.docstatus,
                "Stock Entry Type": se.stock_entry_type,
                "Company": se.company,
                "Posting Date": se.posting_date,       # <-- new
                "Posting Time": se.posting_time,       # <-- new
                "Default Source Warehouse": se.from_warehouse,
                "Default Target Warehouse": se.to_warehouse,
                "Cost Center": item["cost_center"],
                "Item Code": item["item_code"],        # <-- new
                "Item Name": item["item_name"],
                "Stock Qty": item["qty"],
                "Original Qty": item["custom_original_qty"],
                "Accepted Qty": item["custom_accepted_qty"],
                "Difference Qty": item["custom_difference_qty"]
            })

    # Step 5: Return CSV if requested
    if download and report:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=report[0].keys())
        writer.writeheader()
        writer.writerows(report)
        return output.getvalue()

    return report
