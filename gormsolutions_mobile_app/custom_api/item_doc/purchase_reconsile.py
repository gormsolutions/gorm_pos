import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils import nowdate
import json
from datetime import datetime, time

@frappe.whitelist()
def create_purchase_invoice(items, supplier, posting_date, company=None, is_paid=False):
    """
    Create a Purchase Invoice and optionally mark it as paid.

    Args:
        items (list): List of dicts with item_code, qty, rate, warehouse, uom
        supplier (str): Supplier name
        posting_date (str): Required date string (YYYY-MM-DD)
        company (str): Company name (optional, default user company)
        is_paid (bool): If True, creates a Payment Entry after submission

    Returns:
        dict: {
            "invoice_name": str,
            "payment_entry": str or None
        }
    """
    if not items:
        frappe.throw(_("Items list cannot be empty"))

    if not isinstance(items, list):
        import json
        items = json.loads(items)

    if not supplier:
        frappe.throw(_("Supplier is required"))

    if not posting_date:
        frappe.throw(_("Posting date is required"))

    if not company:
        company = frappe.defaults.get_user_default("Company")
        if not company:
            frappe.throw(_("Company is required"))

    # Create the Purchase Invoice
    doc = frappe.new_doc("Purchase Invoice")
    doc.company = company
    doc.supplier = supplier
    doc.posting_date = posting_date
    doc.update_stock = 1
    doc.set_posting_time = 1  # Always set posting date
    default_warehouse = "Stores - AEL"
    doc.set_warehouse = default_warehouse

    for item in items:
        item_code = item["item_code"]
        uom = item.get("uom", "Nos")
        rate = flt(item.get("rate", 0))
        raw_qty = flt(item.get("qty", 0))

        # Get conversion factor for the item and UOM
        conversion_factor = get_uom_conversion_factor(item_code, uom)

        # Use appropriate precision
        precision = 0 if conversion_factor == int(conversion_factor) else 2
        qty = flt(raw_qty, precision)

        stock_qty = qty * conversion_factor

        doc.append("items", {
            "item_code": item_code,
            "qty": qty,
            "uom": uom,
            "rate": rate,
            "warehouse": default_warehouse,
            "conversion_factor": conversion_factor,
            "stock_qty": stock_qty,
            "expense_account": item.get("expense_account", "1410 - Stock In Hand - AEL")
        })

    doc.insert(ignore_permissions=True)
    doc.submit()

    payment_entry_name = None
    if frappe.utils.cint(is_paid):
        payment_entry_name = create_payment_entry_for_invoice(doc.name, posting_date, company)

    return {
        "invoice_name": doc.name,
        "payment_entry": payment_entry_name
    }

def get_uom_conversion_factor(item_code, uom):
    """
    Fetch the conversion factor from the Item UOM table.
    """
    cf = frappe.db.get_value("UOM Conversion Detail", {
        "parent": item_code,
        "uom": uom
    }, "conversion_factor")

    if not cf:
        frappe.throw(_("Conversion factor for UOM '{0}' not found for item '{1}'").format(uom, item_code))

    return flt(cf)


def get_uom_precision(uom):
    """
    Returns 0 if UOM is marked as 'Must be Whole Number',
    otherwise defaults to 2 decimal places.
    """
    must_be_whole = frappe.db.get_value("UOM", uom, "must_be_whole_number")
    if must_be_whole:
        return 0
    else:
        return 2


def create_payment_entry_for_invoice(purchase_invoice_name, posting_date, company):
    invoice = frappe.get_doc("Purchase Invoice", purchase_invoice_name)

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Pay"
    pe.party_type = "Supplier"
    pe.party = invoice.supplier
    pe.posting_date = posting_date
    pe.paid_to = invoice.credit_to
    pe.reference_no = "from mobile app"
    pe.reference_date = posting_date
    # pe.mode_of_payment = frappe.get_value("Mode of Payment", {"is_default": 1}, "name") or frappe.throw(_("Set a default Mode of Payment"))
    pe.company = invoice.company
    pe.paid_from_account_currency = frappe.db.get_value("Account", pe.paid_from, "account_currency")
    pe.paid_to_account_currency = invoice.currency
    pe.source_exchange_rate = 1.0  # Default exchange rate, can be adjusted if needed

    # Set paid_from (bank/cash account) - must be set in company default
    pe.paid_from = frappe.get_value("Company", company, "default_cash_account") or frappe.throw(_("Set default Cash account for company"))

    # Paid_to is the supplier's payable account on the invoice
    pe.paid_to = invoice.credit_to
    pe.company = company

    # Mode of Payment (default)
    # pe.mode_of_payment = frappe.get_value("Mode of Payment", {"is_default": 1}, "name") or frappe.throw(_("Set a default Mode of Payment"))

    # Currency & exchange rates
    pe.paid_from_account_currency = frappe.db.get_value("Account", pe.paid_from, "account_currency")
    pe.paid_to_account_currency = invoice.currency
    pe.source_exchange_rate = 1.0  # You can modify this if exchange rate differs

    # Amounts
    pe.paid_amount = invoice.rounded_total or invoice.grand_total
    pe.received_amount = pe.paid_amount

    # Append reference to link payment entry with the invoice
    pe.append("references", {
        "reference_doctype": "Purchase Invoice",
        "reference_name": invoice.name,
        "total_amount": invoice.grand_total,
        "allocated_amount": invoice.grand_total
    })

    pe.insert(ignore_permissions=True)
    pe.submit()

    return pe.name




@frappe.whitelist(allow_guest=False)
def create_stock_reconciliation_via_api(data):
    """
    Accepts a JSON payload to create a Stock Reconciliation document dynamically
    """
    try:
        if isinstance(data, str):
            data = json.loads(data)

        doc = frappe.new_doc("Stock Reconciliation")
        doc.naming_series = data.get("naming_series", "MAT-RECO-.YYYY.-")
        doc.company = "ASHLINK ENTERPRISE LTD"
        doc.purpose = data.get("purpose")

        # Posting date fallback to today
        doc.posting_date = data.get("posting_date") or nowdate()
        doc.set_posting_date = 1 if data.get("set_posting_date") else 0

        # Handle posting_time if set_posting_time is True and posting_time is provided
        if data.get("set_posting_time") and data.get("posting_time"):
            # Convert string time "HH:MM:SS" to a time object
            try:
                posting_time_str = data.get("posting_time")
                h, m, s = map(int, posting_time_str.split(":"))
                doc.posting_time = time(h, m, s)
                doc.set_posting_time = 1
            except Exception:
                # If parsing fails, fallback or skip
                doc.set_posting_time = 0
        else:
            doc.set_posting_time = 0
            
        default_warehouse = "Stores - AEL"

        doc.set_warehouse = default_warehouse
        doc.scan_mode = data.get("scan_mode", 0)
        doc.expense_account = "1910 - Temporary Opening - AEL"
        doc.cost_center = "Main - AEL"

        for item in data.get("items", []):
            doc.append("items", {
                "item_code": item["item_code"],
                "qty": item["qty"],
                "valuation_rate": item["valuation_rate"],
                "warehouse":default_warehouse
            })

        doc.insert()
        doc.submit()
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Stock Reconciliation created"),
            "name": doc.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "API: Stock Reconciliation Creation Failed")
        return {
            "status": "error",
            "message": str(e)
        }
