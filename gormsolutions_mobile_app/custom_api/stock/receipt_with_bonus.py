import frappe
from frappe.utils import nowdate

def insert_free_stock_entry_direct(supplier, items, warehouse="Stores - AEL", posting_date=None):
    if not posting_date:
        posting_date = nowdate()

    try:
        # Create Stock Entry doc
        se_name = frappe.db.get_new_docname("Stock Entry")
        frappe.db.sql("""
            INSERT INTO `tabStock Entry` 
            (`name`, `posting_date`, `purpose`, `remarks`, `docstatus`, `owner`, `creation`, `modified`) 
            VALUES (%s, %s, %s, %s, 1, %s, NOW(), NOW())
        """, (se_name, posting_date, "Material Receipt", f"Free items from {supplier}", supplier))

        # Insert Stock Entry Items
        for idx, i in enumerate(items, start=1):
            se_detail_name = frappe.db.get_new_docname("Stock Entry Detail")
            frappe.db.sql("""
                INSERT INTO `tabStock Entry Detail` 
                (`name`, `parent`, `parentfield`, `parenttype`, `idx`, `item_code`, `qty`, `transfer_qty`, `uom`, `s_warehouse`, `basic_rate`, `amount`) 
                VALUES (%s, %s, 'items', 'Stock Entry', %s, %s, %s, %s, %s, %s, 0, 0)
            """, (se_detail_name, se_name, idx, i["item_code"], i["qty"], i["qty"], i["uom"], warehouse))

        frappe.db.commit()
        return {"status": "success", "stock_entry": se_name}

    except Exception as e:
        frappe.db.rollback()
        return {"status": "error", "message": str(e)}
