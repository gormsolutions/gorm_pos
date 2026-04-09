import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def create_stock_transfer(docname):
    doc = frappe.get_doc("Batch Work Order", docname)

    if not doc.source_warehouse or not doc.wip_warehouse:
        frappe.throw("Please set both Source and WIP Warehouse.")

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Transfer"
    stock_entry.company = doc.company
    stock_entry.from_warehouse = doc.source_warehouse
    stock_entry.to_warehouse = doc.wip_warehouse
    stock_entry.posting_date = nowdate()
    stock_entry.set_posting_time = 1

    for item in doc.required_items:
        if item.additional:
            stock_entry.append("items", {
                "item_code": item.item_code,
                "qty": item.required_qty,
                "uom": frappe.db.get_value("Item", item.item_code, "stock_uom"),
                "s_warehouse": doc.source_warehouse,
                "t_warehouse": doc.wip_warehouse
            })

    if not stock_entry.items:
        frappe.throw("No additional items found in the Required Items table.")

    stock_entry.insert()
    stock_entry.submit()  # ✅ Submit the stock entry

    return stock_entry.name  # ✅ No redirect/route logic
