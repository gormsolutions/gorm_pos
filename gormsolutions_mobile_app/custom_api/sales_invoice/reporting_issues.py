import frappe
import json
from frappe.utils import nowdate

@frappe.whitelist()
def get_deleted_sales_invoices_html(from_date=None, to_date=None):
    """
    Return raw HTML of ALL deleted Sales Invoices strictly between from_date and to_date (24 hrs each day)
    """
    if not from_date:
        from_date = nowdate()
    if not to_date:
        to_date = from_date

    # Convert to datetime strings for filter
    start_dt = f"{from_date} 00:00:00"
    end_dt = f"{to_date} 23:59:59"

    filters = {
        "deleted_doctype": "Sales Invoice",
        "creation": ("between", [start_dt, end_dt])
    }

    all_deleted_docs = []
    batch_size = 1000
    start = 0

    while True:
        batch = frappe.get_all(
            "Deleted Document",
            filters=filters,
            fields=["name", "deleted_name", "data", "creation", "owner"],
            order_by="creation asc",
            limit_start=start,
            limit_page_length=batch_size
        )
        if not batch:
            break
        all_deleted_docs.extend(batch)
        start += batch_size

    invoices = []

    for dd in all_deleted_docs:
        data_json = dd.get("data") or "{}"
        try:
            doc = json.loads(data_json)
        except Exception:
            doc = {}

        invoice_name = doc.get("name") or "N/A"
        deleted_name = dd.get("deleted_name") or "N/A"
        deleted_by = dd.get("owner") or "N/A"  # Owner of Deleted Document
        deletion_date = dd.get("creation") or ""  # When it was deleted
        custom_from = doc.get("custom_from") or "N/A"
        grand_total = doc.get("grand_total") or 0
        customer = doc.get("customer_name") or doc.get("customer") or "N/A"
        posting_date = doc.get("posting_date") or "N/A"
        items = doc.get("items") or []

        if not items:
            items = [{
                "item_code": "",
                "item_name": "",
                "qty": 0,
                "rate": 0,
                "amount": 0,
                "item_cost_center": doc.get("cost_center") or ""
            }]

        for it in items:
            it["item_code"] = it.get("item_code") or it.get("item") or ""
            it["item_name"] = it.get("item_name") or it.get("description") or ""
            it["qty"] = it.get("qty") or it.get("quantity") or 0
            it["rate"] = it.get("rate") or it.get("price_list_rate") or 0
            it["amount"] = it.get("amount") or it.get("base_amount") or 0
            it["item_cost_center"] = it.get("cost_center") or ""

        invoices.append({
            "invoice_name": invoice_name,
            "deleted_name": deleted_name,
            "deleted_by": deleted_by,
            "custom_from": custom_from,
            "deletion_date": deletion_date,
            "grand_total": grand_total,
            "customer": customer,
            "posting_date": posting_date,
            "items": items
        })

    # Build HTML
    html = f"<h2 style='text-align:center;'>Deleted Sales Invoices Report</h2><p><b>From:</b> {from_date} <b>To:</b> {to_date}</p>"

    for inv in invoices:
        html += f"""
        <h3>Invoice: {inv['invoice_name']} | Deleted Name: {inv['deleted_name']}</h3>
        <p>
            <b>From:</b> {inv['custom_from']} | 
            <b>Customer:</b> {inv['customer']} | 
            <b>Deleted By:</b> {inv['deleted_by']} | 
            <b>Deletion Date:</b> {inv['deletion_date']} | 
            <b>Posting Date:</b> {inv['posting_date']}
        </p>
        <table border="1" cellspacing="0" cellpadding="4" width="100%" style="border-collapse:collapse;">
            <thead style="background-color:#f2f2f2;">
                <tr>
                    <th>Item Code</th>
                    <th>Item Name</th>
                    <th>Qty</th>
                    <th>Rate</th>
                    <th>Amount</th>
                    <th>Cost Center</th>
                </tr>
            </thead>
            <tbody>
        """
        for it in inv["items"]:
            html += f"""
            <tr>
                <td>{it['item_code']}</td>
                <td>{it['item_name']}</td>
                <td>{it['qty']}</td>
                <td>{it['rate']:.2f}</td>
                <td>{it['amount']:.2f}</td>
                <td>{it['item_cost_center']}</td>
            </tr>
            """
        html += f"</tbody></table><p><b>Grand Total:</b> {inv['grand_total']:.2f}</p><hr>"

    if not invoices:
        html += "<p>No deleted Sales Invoices found for this period.</p>"

    return html
