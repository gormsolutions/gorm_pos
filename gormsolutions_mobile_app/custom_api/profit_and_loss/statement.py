
import frappe
from frappe import _
from frappe.utils import flt

@frappe.whitelist()
def get_grouped_profit_and_loss(from_date, to_date, cost_center=None, company=None):
    filters = {
        "posting_date": ["between", [from_date, to_date]],
        "voucher_subtype": ["!=", "Internal Transfer"],  # Exclude 'Internal Transfer'
        "is_cancelled": 0
    }
    if cost_center:
        filters["cost_center"] = cost_center
    if company:
        filters["company"] = company

    gl_entries = frappe.get_all(
        "GL Entry",
        filters=filters,
        fields=[
            "name as voucher_number",
            "voucher_no",
            "posting_date",
            "account",
            "debit",
            "credit",
            "against_voucher",
            "against_voucher_type",
            "party_type",
            "party",
            "voucher_subtype",
            "company"  # optional, useful for debugging or UI display
        ],
        order_by="posting_date asc"
    )

    grouped_data = {
        "Expenses": {"total": 0.0, "entries": []},
        "Invoices": {"total": 0.0, "entries": []},
        "Other": {"total": 0.0, "entries": []}
    }

    for entry in gl_entries:
        if not entry["account"]:
            continue

        account_doc = frappe.get_doc("Account", entry["account"])
        parent_account = account_doc.parent_account
        account_type = account_doc.account_type
        root_type = account_doc.root_type

        # Exclude entries with parent account 4100 - Direct Income - CCML
        if parent_account == "4100 - Direct Income - CCML":
            continue

        # Only process if root_type is either 'Income' or 'Expense'
        if root_type not in ["Income", "Expense"]:
            continue

        debit_amount = flt(entry.get("debit", 0))
        credit_amount = flt(entry.get("credit", 0))
        amount = debit_amount - credit_amount

        # Categorize and group entries
        if root_type == "Expense":   # ✅ all expenses (COGS + operating)
            grouped_data["Expenses"]["total"] += amount
            grouped_data["Expenses"]["entries"].append(entry)
        elif any(x in account_type for x in ["Income Account", "Bank", "Cash"]):
            grouped_data["Invoices"]["total"] += amount
            grouped_data["Invoices"]["entries"].append(entry)
        else:
            grouped_data["Other"]["total"] += amount
            grouped_data["Other"]["entries"].append(entry)

    # Calculate Total Income (Credits from Invoices + Other income)
    total_income = sum(flt(entry.get("credit", 0)) for entry in grouped_data["Invoices"]["entries"])
    total_income += sum(flt(entry.get("credit", 0)) for entry in grouped_data["Other"]["entries"])

    # Calculate Total Expense (Debits from all expenses)
    total_expense = sum(flt(entry.get("debit", 0)) for entry in grouped_data["Expenses"]["entries"])

    # Net Profit = Total Income - Total Expense
    net_profit = total_income - total_expense

    total_debit = sum([group["total"] for group in grouped_data.values()])
    total_credit = total_debit  # Assuming debit and credit are balanced

    return {
        "grouped_data": grouped_data,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": net_profit,
        "total_debit": total_debit,
        "total_credit": total_credit,
    }


import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_gross_profit_grouped(from_date, to_date, company=None, cost_center=None, warehouse=None):
    """
    Correct Gross Profit grouped by Item Group with per-item breakdown,
    matching ERPNext Gross Profit Report logic.
    """
    # Build filters
    si_filters = ["si.docstatus = 1", "si.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
    if company:
        si_filters.append("si.company = %(company)s")
    if cost_center:
        si_filters.append("(COALESCE(sii.cost_center, si.cost_center) = %(cost_center)s)")
    if warehouse:
        si_filters.append("(COALESCE(sii.warehouse, si.warehouse) = %(warehouse)s)")

    where_clause = " AND ".join(si_filters)

    # Pull Sales Invoice Items
    invoice_items = frappe.db.sql(
        f"""
        SELECT
            sii.name AS sii_name,
            sii.parent AS invoice_name,
            sii.item_group,
            sii.item_code,
            sii.item_name,
            sii.qty,
            sii.base_net_amount AS selling_amount
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE {where_clause}
        ORDER BY sii.item_group, sii.item_name
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
            "cost_center": cost_center,
            "warehouse": warehouse,
        },
        as_dict=True,
    )

    # For each invoice item, fetch exact buying amount using SLE
    for item in invoice_items:
        sle_rows = frappe.db.sql("""
            SELECT actual_qty, valuation_rate
            FROM `tabStock Ledger Entry`
            WHERE voucher_type='Sales Invoice'
              AND voucher_no=%(invoice)s
              AND voucher_detail_no=%(sii_name)s
              AND is_cancelled=0
        """, {"invoice": item.invoice_name, "sii_name": item.sii_name}, as_dict=True)

        buying_amount = 0.0
        for sle in sle_rows:
            # ERPNext stores outgoing items as negative qty
            buying_amount += -1 * flt(sle.actual_qty) * flt(sle.valuation_rate)

        item["buying_amount"] = buying_amount
        item["gross_profit"] = flt(item["selling_amount"]) - buying_amount
        item["avg_selling_rate"] = flt(item["selling_amount"]) / flt(item["qty"]) if item["qty"] else 0.0
        item["valuation_rate"] = flt(buying_amount) / flt(item["qty"]) if item["qty"] else 0.0
        item["gross_profit_percent"] = (item["gross_profit"] / item["selling_amount"] * 100) if item["selling_amount"] else 0.0

    # Group by item_group
    grouped = {}
    for item in invoice_items:
        group = item.item_group or "Uncategorized"
        if group not in grouped:
            grouped[group] = {
                "item_group": group,
                "total_qty": 0.0,
                "total_selling": 0.0,
                "total_buying": 0.0,
                "total_gross_profit": 0.0,
                "total_gross_profit_percent": 0.0,
                "items": []
            }

        grouped[group]["items"].append(item)
        grouped[group]["total_qty"] += flt(item["qty"])
        grouped[group]["total_selling"] += flt(item["selling_amount"])
        grouped[group]["total_buying"] += flt(item["buying_amount"])
        grouped[group]["total_gross_profit"] += flt(item["gross_profit"])

    # Compute group-level percentages
    for g in grouped.values():
        g["total_gross_profit_percent"] = (g["total_gross_profit"] / g["total_selling"] * 100) if g["total_selling"] else 0.0

    return list(grouped.values())
