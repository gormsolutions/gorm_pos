import frappe

@frappe.whitelist()
def get_party_outstandings_with_items_and_company(from_date=None, to_date=None, cost_center=None, company=None):
    """
    Fetch outstanding balances for customers and suppliers, grouped by party, including invoice details with items.
    """
    
    # Fetch outstanding balances for Customers (No Filters)
    customer_entries = frappe.db.sql("""
        SELECT 
            gle.party AS party_name,
            'Customer' AS party_type,
            SUM(gle.debit - gle.credit) AS balance
        FROM `tabGL Entry` gle
        WHERE gle.party_type = 'Customer'
        GROUP BY gle.party
    """, as_dict=True)

    # Fetch outstanding balances for Suppliers (No Filters)
    supplier_entries = frappe.db.sql("""
        SELECT 
            gle.party AS party_name,
            'Supplier' AS party_type,
            SUM(gle.credit - gle.debit) AS balance
        FROM `tabGL Entry` gle
        WHERE gle.party_type = 'Supplier'
        GROUP BY gle.party
    """, as_dict=True)

    # Prepare conditions and filters for invoices
    conditions = "si.docstatus = 1 AND si.outstanding_amount > 0"
    supplier_conditions = "pi.docstatus = 1 AND pi.outstanding_amount > 0"
    filters = []

    if from_date and to_date:
        conditions += " AND si.posting_date BETWEEN %s AND %s"
        supplier_conditions += " AND pi.posting_date BETWEEN %s AND %s"
        filters.extend([from_date, to_date])
    
    if company:
        conditions += " AND si.company = %s"
        supplier_conditions += " AND pi.company = %s"
        filters.append(company)

    # Fetch outstanding customer invoices
    customer_invoices = frappe.db.sql(f"""
        SELECT 
            si.customer AS party_name,
            si.name AS invoice_no,
            si.posting_date,
            si.outstanding_amount
        FROM `tabSales Invoice` si
        WHERE {conditions}
    """, tuple(filters), as_dict=True)

    # Fetch outstanding supplier invoices
    supplier_invoices = frappe.db.sql(f"""
        SELECT 
            pi.supplier AS party_name,
            pi.name AS invoice_no,
            pi.posting_date,
            pi.outstanding_amount
        FROM `tabPurchase Invoice` pi
        WHERE {supplier_conditions}
    """, tuple(filters), as_dict=True)

    # Fetch Sales Invoice Items
    customer_items = frappe.db.sql("""
        SELECT 
            sii.parent AS invoice_no,
            sii.item_code,
            sii.item_name,
            sii.qty,
            sii.uom,
            sii.rate
        FROM `tabSales Invoice Item` sii
    """, as_dict=True)

    # Fetch Purchase Invoice Items
    supplier_items = frappe.db.sql("""
        SELECT 
            pii.parent AS invoice_no,
            pii.item_code,
            pii.item_name,
            pii.qty,
            pii.uom,
            pii.rate
        FROM `tabPurchase Invoice Item` pii
    """, as_dict=True)

    # Organize invoices with their items
    customer_invoice_map = {inv["invoice_no"]: inv for inv in customer_invoices}
    supplier_invoice_map = {inv["invoice_no"]: inv for inv in supplier_invoices}

    for item in customer_items:
        if item["invoice_no"] in customer_invoice_map:
            customer_invoice_map[item["invoice_no"]].setdefault("items", []).append(item)

    for item in supplier_items:
        if item["invoice_no"] in supplier_invoice_map:
            supplier_invoice_map[item["invoice_no"]].setdefault("items", []).append(item)

    # Enrich results with customer and supplier names
    customers = []
    for entry in customer_entries:
        customer_name = frappe.db.get_value("Customer", entry["party_name"], "customer_name")
        customer_data = {
            "party_name": entry["party_name"],
            "party_type": "Customer",
            "balance": entry["balance"],
            "customer_name": customer_name,
            "invoices": [customer_invoice_map[inv] for inv in customer_invoice_map if customer_invoice_map[inv]["party_name"] == entry["party_name"]]
        }
        customers.append(customer_data)

    suppliers = []
    for entry in supplier_entries:
        supplier_name = frappe.db.get_value("Supplier", entry["party_name"], "supplier_name")
        supplier_data = {
            "party_name": entry["party_name"],
            "party_type": "Supplier",
            "balance": entry["balance"],
            "supplier_name": supplier_name,
            "invoices": [supplier_invoice_map[inv] for inv in supplier_invoice_map if supplier_invoice_map[inv]["party_name"] == entry["party_name"]]
        }
        suppliers.append(supplier_data)

    return {
        "customers": customers,
        "suppliers": suppliers
    }

import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_sales_invoice_details_and_payments(customer, from_date, to_date):
    sales_invoice_data = []
    total_paid_amount = 0
    grand_total_amount = 0  # Variable to hold the grand total of all amounts
    running_balance = 0      # Variable to hold the running balance
    balance_brought_forward = 0  # Variable to hold the balance brought forward

    # Calculate Balance Brought Forward (balance before the 'from_date')
    previous_balance = frappe.db.sql("""
        SELECT 
            SUM(gle.debit - gle.credit) AS balance
        FROM 
            `tabGL Entry` gle
        WHERE 
            gle.party_type = 'Customer'
            AND gle.party = %s
            AND gle.posting_date < %s
            AND gle.docstatus = 1
    """, (customer, from_date), as_dict=True)
    
    if previous_balance and previous_balance[0].balance:
        balance_brought_forward = flt(previous_balance[0].balance)
    
    # Initialize running balance with balance brought forward
    running_balance = balance_brought_forward

    # Step 1: Fetch Sales Invoices and their items for the specified customer and date range
    invoices = frappe.db.sql("""
        SELECT 
            si.name AS invoice_name,
            si.posting_date,
            si.cost_center, 
            si.status, 
            sii.item_code, 
            sii.qty, 
            sii.uom,
            sii.rate, 
            sii.amount
        FROM 
            `tabSales Invoice` si
        JOIN 
            `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE 
            si.customer = %s 
            AND si.posting_date BETWEEN %s AND %s 
            AND si.docstatus = 1
    """, (customer, from_date, to_date), as_dict=True)

    for invoice in invoices:
        total_amount = flt(invoice.amount)
        grand_total_amount += total_amount  # Add to grand total
        running_balance += total_amount  # Update running balance 
        
        invoice_data = {
            "invoice_name": invoice.invoice_name,
            "cost_center":invoice.cost_center,
            "posting_date": invoice.posting_date,  # Add posting date to the invoice data
            "item_code": invoice.item_code,
            "status": invoice.status,
            "qty": flt(invoice.qty),
            "rate": flt(invoice.rate),
            "uom": invoice.uom,
            "amount": total_amount,
            "running_balance": running_balance  # Include running balance for each invoice
        }
        
        sales_invoice_data.append(invoice_data)

    # Step 2: Fetch Payment Entries within the specified date range for the same customer
    payments = frappe.db.sql("""
        SELECT 
            pe.name AS payment_entry_name, 
            pe.posting_date,
            pe.cost_center, 
            pe.paid_amount
        FROM 
            `tabPayment Entry` pe
        WHERE 
            pe.party_type = 'Customer'
            AND pe.party = %s
            AND pe.posting_date BETWEEN %s AND %s
            AND pe.docstatus = 1
    """, (customer, from_date, to_date), as_dict=True)

    filtered_payments = []
    for payment in payments:
        total_paid_amount += flt(payment.paid_amount)
        running_balance -= flt(payment.paid_amount)  # Subtract payment from running balance
        filtered_payments.append({
            "payment_entry_name": payment.payment_entry_name,
            "cost_center": payment.cost_center,
            "posting_date": payment.posting_date,  # Include posting date for payments
            "paid_amount": payment.paid_amount
        })

    # Step 3: Fetch GL Entries for the customer where voucher type is Journal Entry
    gl_entries = frappe.db.sql("""
        SELECT
            gle.name AS gl_entry_name,
            gle.posting_date,
            gle.cost_center,
            gle.debit,
            gle.voucher_no,
            gle.credit,
            gle.remarks
        FROM
            `tabGL Entry` gle
        WHERE
            gle.party_type = 'Customer'
            AND gle.party = %s
            AND gle.voucher_type = 'Journal Entry'
            AND gle.posting_date BETWEEN %s AND %s
            AND gle.docstatus = 1
    """, (customer, from_date, to_date), as_dict=True)

    filtered_gl_entries = []
    for gl_entry in gl_entries:
        filtered_gl_entries.append({
            "gl_entry_name": gl_entry.gl_entry_name,
            "posting_date": gl_entry.posting_date,
            "cost_center": gl_entry.cost_center,
            "voucher_no": gl_entry.voucher_no,
            "debit": flt(gl_entry.debit),
            "credit": flt(gl_entry.credit),
            "remarks": gl_entry.remarks
        })

        # Update running balance: add debit amounts and subtract credit amounts
        running_balance += flt(gl_entry.debit)  # Add debit to running balance
        running_balance -= flt(gl_entry.credit)  # Subtract credit from running balance
        total_paid_amount += flt(gl_entry.credit)  # Add credit to total paid

    # Calculate outstanding amount
    outstanding_amount = grand_total_amount - total_paid_amount

    return {
        "sales_invoice_data": sales_invoice_data,
        "balance_brought_forward": balance_brought_forward,  # Include the balance brought forward
        "grand_total_amount": grand_total_amount,  # Return grand total of all amounts
        "total_paid_amount": total_paid_amount,
        "outstanding_amount": outstanding_amount,  # Return outstanding amount
        "payments": filtered_payments,  # Include filtered payment details in the result
        "gl_entries": filtered_gl_entries  # Include filtered GL entries in the result
    }


@frappe.whitelist()
def supplier_details_and_payments(supplier, from_date, to_date):
    purchase_invoice_data = []
    total_paid_amount = 0
    grand_total_amount = 0  # Variable to hold the grand total of all amounts
    running_balance = 0      # Variable to hold the running balance
    balance_brought_forward = 0  # Variable to hold the balance brought forward

    # Calculate Balance Brought Forward (balance before the 'from_date')
    previous_balance = frappe.db.sql("""
        SELECT 
            SUM(gle.debit - gle.credit) AS balance
        FROM 
            `tabGL Entry` gle
        WHERE 
            gle.party_type = 'Supplier'
            AND gle.party = %s
            AND gle.posting_date < %s
            AND gle.docstatus = 1
    """, (supplier, from_date), as_dict=True)
    
    if previous_balance and previous_balance[0].balance:
        balance_brought_forward = flt(previous_balance[0].balance)
    
    # Initialize running balance with balance brought forward
    running_balance = balance_brought_forward

    # Step 1: Fetch Sales Invoices and their items for the specified customer and date range
    invoices = frappe.db.sql("""
        SELECT 
            si.name AS invoice_name,
            si.posting_date,
            si.cost_center, 
            si.status, 
            sii.item_code,
            sii.uom, 
            sii.qty, 
            sii.rate, 
            sii.amount
        FROM 
            `tabPurchase Invoice` si
        JOIN 
            `tabPurchase Invoice Item` sii ON sii.parent = si.name
        WHERE 
            si.supplier = %s 
            AND si.posting_date BETWEEN %s AND %s 
            AND si.docstatus = 1
    """, (supplier, from_date, to_date), as_dict=True)

    for invoice in invoices:
        total_amount = flt(invoice.amount)
        grand_total_amount += total_amount  # Add to grand total
        running_balance += total_amount  # Update running balance 
        
        invoice_data = {
            "invoice_name": invoice.invoice_name,
            "cost_center":invoice.cost_center,
            "posting_date": invoice.posting_date,  # Add posting date to the invoice data
            "item_code": invoice.item_code,
            "status": invoice.status,
            "uom": invoice.uom,
            "qty": flt(invoice.qty),
            "rate": flt(invoice.rate),
            "amount": total_amount,
            "running_balance": running_balance  # Include running balance for each invoice
        }
        
        purchase_invoice_data.append(invoice_data)

    # Step 2: Fetch Payment Entries within the specified date range for the same customer
    payments = frappe.db.sql("""
        SELECT 
            pe.name AS payment_entry_name, 
            pe.posting_date,
            pe.cost_center, 
            pe.paid_amount
        FROM 
            `tabPayment Entry` pe
        WHERE 
            pe.party_type = 'Supplier'
            AND pe.party = %s
            AND pe.posting_date BETWEEN %s AND %s
            AND pe.docstatus = 1
    """, (supplier, from_date, to_date), as_dict=True)

    filtered_payments = []
    for payment in payments:
        total_paid_amount += flt(payment.paid_amount)
        running_balance -= flt(payment.paid_amount)  # Subtract payment from running balance
        filtered_payments.append({
            "payment_entry_name": payment.payment_entry_name,
            "cost_center": payment.cost_center,
            "posting_date": payment.posting_date,  # Include posting date for payments
            "paid_amount": payment.paid_amount
        })

    # Step 3: Fetch GL Entries for the customer where voucher type is Journal Entry
    gl_entries = frappe.db.sql("""
        SELECT
            gle.name AS gl_entry_name,
            gle.posting_date,
            gle.cost_center,
            gle.debit,
            gle.voucher_no,
            gle.credit,
            gle.remarks
        FROM
            `tabGL Entry` gle
        WHERE
            gle.party_type = 'Supplier'
            AND gle.party = %s
            AND gle.voucher_type = 'Journal Entry'
            AND gle.posting_date BETWEEN %s AND %s
            AND gle.docstatus = 1
    """, (supplier, from_date, to_date), as_dict=True)

    filtered_gl_entries = []
    for gl_entry in gl_entries:
        filtered_gl_entries.append({
            "gl_entry_name": gl_entry.gl_entry_name,
            "posting_date": gl_entry.posting_date,
            "cost_center": gl_entry.cost_center,
            "voucher_no": gl_entry.voucher_no,
            "debit": flt(gl_entry.debit),
            "credit": flt(gl_entry.credit),
            "remarks": gl_entry.remarks
        })

        # Update running balance: add debit amounts and subtract credit amounts
        running_balance += flt(gl_entry.debit)  # Add debit to running balance
        running_balance -= flt(gl_entry.credit)  # Subtract credit from running balance
        total_paid_amount += flt(gl_entry.credit)  # Add credit to total paid

    # Calculate outstanding amount
    outstanding_amount = grand_total_amount - total_paid_amount

    return {
        "purchase_invoice_data": purchase_invoice_data,
        "balance_brought_forward": balance_brought_forward,  # Include the balance brought forward
        "grand_total_amount": grand_total_amount,  # Return grand total of all amounts
        "total_paid_amount": total_paid_amount,
        "outstanding_amount": outstanding_amount,  # Return outstanding amount
        "payments": filtered_payments,  # Include filtered payment details in the result
        "gl_entries": filtered_gl_entries  # Include filtered GL entries in the result
    }

@frappe.whitelist()
def get_transaction_report_gl(transaction_id, station=None, from_date=None, to_date=None):
    # Fetch the Transaction Accounts document
    transaction_account_doc = frappe.get_doc("Transaction Accounts", transaction_id)
    account_names = [item.account for item in transaction_account_doc.trans_account_items]

    # Initialize conditions and parameters
    conditions = ["is_cancelled = 0"]  # Exclude canceled entries
    params = {}

    # Add conditions based on optional filters
    if station:
        conditions.append("cost_center = %(cost_center)s")
        params["cost_center"] = station

    if from_date and to_date:
        conditions.append("posting_date BETWEEN %(from_date)s AND %(to_date)s")
        params["from_date"] = from_date
        params["to_date"] = to_date

    # Combine conditions into a single string
    condition_str = " AND ".join(conditions)

    # Query the GL Entry table
    debit_credit_data = frappe.db.sql(f"""
        SELECT 
            account, 
            SUM(debit) - SUM(credit) AS balance
        FROM 
            `tabGL Entry`
        WHERE 
            account IN %(account_names)s 
            {"AND " + condition_str if condition_str else ""}
        GROUP BY 
            account
    """, {
        "account_names": account_names,
        **params
    }, as_dict=True)

    return debit_credit_data
