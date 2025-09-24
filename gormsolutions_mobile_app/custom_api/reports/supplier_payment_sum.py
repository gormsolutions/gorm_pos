import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_supplier_payment_details(from_date=None, to_date=None, company=None, cost_center=None, supplier=None):
    """
    Return detailed report of supplier transactions (invoices + payments).
    Filters by company, cost center, supplier, and date range.
    
    Each row contains:
        posting_date, voucher_type, voucher_no, supplier, supplier_name,
        company, cost_center, debit (invoices), credit (payments).
    """
    conditions = "gle.party_type = 'Supplier' AND gle.is_cancelled = 0"
    values = {}

    if company:
        conditions += " AND gle.company = %(company)s"
        values["company"] = company

    if cost_center:
        conditions += " AND gle.cost_center = %(cost_center)s"
        values["cost_center"] = cost_center

    if supplier:
        conditions += " AND gle.party = %(supplier)s"
        values["supplier"] = supplier

    if from_date:
        conditions += " AND gle.posting_date >= %(from_date)s"
        values["from_date"] = from_date

    if to_date:
        conditions += " AND gle.posting_date <= %(to_date)s"
        values["to_date"] = to_date

    query = f"""
        SELECT
            gle.posting_date,
            gle.voucher_type,
            gle.voucher_no,
            gle.party AS supplier,
            sup.supplier_name,
            gle.company,
            gle.cost_center,
            gle.debit AS invoice_amount,
            gle.credit AS payment_amount
        FROM `tabGL Entry` gle
        LEFT JOIN `tabSupplier` sup ON sup.name = gle.party
        WHERE {conditions}
        ORDER BY gle.posting_date DESC, gle.voucher_no
    """

    results = frappe.db.sql(query, values, as_dict=True)

    # Format numeric values
    for r in results:
        r["invoice_amount"] = flt(r["invoice_amount"])
        r["payment_amount"] = flt(r["payment_amount"])

    return results
