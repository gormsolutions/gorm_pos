import frappe
from frappe.utils import flt, today
from collections import defaultdict
from frappe import _
from collections import defaultdict
from frappe.utils import today, flt
import frappe

@frappe.whitelist(allow_guest=True)
def get_user_day_transactions(from_date=None, to_date=None):
    """
    Returns all transactions within from_date → to_date for the logged-in user:
    - Sales Invoices (POS + Credit/Outstanding)
    - Payment Entries (Receive & Transfer)
    - Branch Expenses (with Expense Claim Items)
    Includes detailed breakdown by mode of payment.
    """

    if not from_date:
        from_date = today()
    if not to_date:
        to_date = from_date

    logged_in_user = frappe.session.user

    # ----------------------------
    # 1. Sales Invoices
    # ----------------------------
    sales_invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
            "owner": logged_in_user
        },
        fields=[
            "name", "customer_name", "grand_total",
            "paid_amount", "outstanding_amount",
            "is_pos", "remarks", "posting_date"
        ]
    )

    # Attach modes for POS invoices
    for inv in sales_invoices:
        inv["modes"] = []
        if inv.is_pos:
            payments = frappe.get_all(
                "Sales Invoice Payment",
                filters={"parent": inv.name},
                fields=["mode_of_payment", "amount"]
            )
            inv["modes"] = payments

    # POS / Cash sales
    total_pos_sales = round(sum(
        flt(inv.grand_total)
        for inv in sales_invoices
        if inv.is_pos or flt(inv.paid_amount) > 0
    ))

    # Outstanding / Credit sales
    total_credit_outstanding = round(sum(
        flt(inv.outstanding_amount)
        for inv in sales_invoices
        if flt(inv.outstanding_amount) > 0
    ))

    # Combined total sales
    total_sales_overall = round(sum(flt(inv.grand_total) for inv in sales_invoices))

    # ----------------------------
    # 2. Payments Received (Payment Entry)
    # ----------------------------
    payments = frappe.get_all(
        "Payment Entry",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
            "payment_type": "Receive",
            "owner": logged_in_user
        },
        fields=[
            "name", "party", "paid_amount",
            "mode_of_payment", "reference_no", "posting_date"
        ]
    )

    total_received = round(sum(flt(p.paid_amount) for p in payments))

    # ----------------------------
    # 3. Internal Transfers (Cash → Bank)
    # ----------------------------
    transfers = frappe.get_all(
        "Payment Entry",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
            "payment_type": "Internal Transfer",
            "owner": logged_in_user
        },
        fields=["name", "paid_amount", "mode_of_payment", "paid_to", "posting_date"]
    )

    total_banked = round(sum(flt(t.paid_amount) for t in transfers))

    # ----------------------------
    # 4. Expenses (Branch Expenses + Expense Claim Items)
    # ----------------------------
    expenses = frappe.get_all(
        "Branch Expenses",
        filters={
            "docstatus": 1,
            "date": ["between", [from_date, to_date]],
            "owner": logged_in_user
        },
        fields=["name", "employee_name", "date"]
    )

    # Attach expense items & compute total
    total_expenses = 0
    for exp in expenses:
        items = frappe.get_all(
            "Expense Claim Items",
            filters={"parent": exp.name},
            fields=["claim_type", "amount", "description"]
        )
        exp["items"] = items
        total_expenses += sum(flt(i.amount) for i in items)
    total_expenses = round(total_expenses)

    # ----------------------------
    # 5. Totals & Balance
    # ----------------------------
    total_cash_at_hand = round((total_pos_sales + total_received))
    balance_at_hand = round((total_pos_sales + total_received) - (total_banked + total_expenses))

    # ----------------------------
    # 6. Payment Mode Breakdown
    # ----------------------------
    payment_modes = defaultdict(float)

    # From POS invoice payments
    for inv in sales_invoices:
        if inv.get("modes"):
            for m in inv["modes"]:
                payment_modes[m.mode_of_payment] += flt(m.amount)

    # From Payment Entries
    for p in payments:
        if p.mode_of_payment:
            payment_modes[p.mode_of_payment] += flt(p.paid_amount)

    # From Transfers
    for t in transfers:
        if t.mode_of_payment:
            payment_modes[t.mode_of_payment] += flt(t.paid_amount)

    # ----------------------------
    # 7. Return Combined Result
    # ----------------------------
    return {
        "from_date": from_date,
        "to_date": to_date,
        "sales_invoices": sales_invoices,
        "payments": payments,
        "transfers": transfers,
        "expenses": expenses,
        "payment_modes": dict(payment_modes),
        "totals": {
            "total_pos_sales": total_pos_sales,
            "total_credit_outstanding": total_credit_outstanding,
            "total_sales_overall": total_sales_overall,
            "total_payments_received": total_received,
            "total_cash_at_hand": total_cash_at_hand,
            "total_banked": total_banked,
            "total_expenses": total_expenses,
            "balance_at_hand": balance_at_hand
        }
    }


from collections import defaultdict
from frappe.utils import today, flt
import frappe

@frappe.whitelist(allow_guest=True)
def get_all_user_day_transactions(from_date=None, to_date=None):
    """
    Returns all transactions within from_date → to_date:
    - Sales Invoices (POS + Credit/Outstanding)
    - Payment Entries (Receive & Transfer)
    - Branch Expenses (with Expense Claim Items)
    And calculates totals & balance at hand grouped by owner,
    including detailed breakdown by Mode of Payment.
    """

    if not from_date:
        from_date = today()
    if not to_date:
        to_date = from_date

    # ----------------------------
    # 1. Sales Invoices
    # ----------------------------
    sales_invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
        },
        fields=[
            "name", "owner", "customer_name", "grand_total",
            "paid_amount", "outstanding_amount",
            "is_pos", "remarks", "posting_date"
        ]
    )

    # Attach mode of payments for POS
    for inv in sales_invoices:
        inv["modes"] = []
        if inv.is_pos:
            payments = frappe.get_all(
                "Sales Invoice Payment",
                filters={"parent": inv.name},
                fields=["mode_of_payment", "amount"]
            )
            inv["modes"] = payments

    sales_by_owner = defaultdict(list)
    for inv in sales_invoices:
        sales_by_owner[inv.owner].append(inv)

    # ----------------------------
    # 2. Payments Received (Payment Entry)
    # ----------------------------
    payments = frappe.get_all(
        "Payment Entry",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
            "payment_type": "Receive",
        },
        fields=[
            "name", "owner", "party", "paid_amount",
            "mode_of_payment", "reference_no", "posting_date"
        ]
    )
    payments_by_owner = defaultdict(list)
    for p in payments:
        payments_by_owner[p.owner].append(p)

    # ----------------------------
    # 3. Internal Transfers (Cash → Bank)
    # ----------------------------
    transfers = frappe.get_all(
        "Payment Entry",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
            "payment_type": "Internal Transfer",
        },
        fields=["name", "owner", "paid_amount", "mode_of_payment", "paid_to", "posting_date"]
    )
    transfers_by_owner = defaultdict(list)
    for t in transfers:
        transfers_by_owner[t.owner].append(t)

    # ----------------------------
    # 4. Expenses (Branch Expenses + Expense Claim Items)
    # ----------------------------
    expenses = frappe.get_all(
        "Branch Expenses",
        filters={
            "docstatus": 1,
            "date": ["between", [from_date, to_date]],
        },
        fields=["name", "owner", "employee_name", "date"]
    )

    expenses_by_owner = defaultdict(list)
    for exp in expenses:
        # attach items
        items = frappe.get_all(
            "Expense Claim Items",
            filters={"parent": exp.name},
            fields=["claim_type", "amount", "description"]
        )
        exp["items"] = items
        expenses_by_owner[exp.owner].append(exp)

    # ----------------------------
    # 5. Compute totals per owner
    # ----------------------------
    report = {}
    all_owners = set(list(sales_by_owner.keys()) + list(payments_by_owner.keys()) +
                     list(transfers_by_owner.keys()) + list(expenses_by_owner.keys()))

    for owner in all_owners:
        invs = sales_by_owner.get(owner, [])
        pms = payments_by_owner.get(owner, [])
        trs = transfers_by_owner.get(owner, [])
        exps = expenses_by_owner.get(owner, [])

        # --- Totals ---
        total_pos_sales = round(sum(flt(inv.grand_total) for inv in invs if inv.is_pos or flt(inv.paid_amount) > 0))
        total_credit_outstanding = round(sum(flt(inv.outstanding_amount) for inv in invs if flt(inv.outstanding_amount) > 0))
        total_sales_overall = round(sum(flt(inv.grand_total) for inv in invs))
        total_received = round(sum(flt(p.paid_amount) for p in pms))
        total_banked = round(sum(flt(t.paid_amount) for t in trs))
        total_expenses = round(sum(flt(i.amount) for exp in exps for i in exp["items"]))
        total_cash_at_hand = round((total_pos_sales + total_received))
        balance_at_hand = round((total_pos_sales + total_received) - (total_banked + total_expenses))

        # --- Payment modes breakdown ---
        payment_modes = defaultdict(float)

        # From POS sales invoice payments
        for inv in invs:
            if inv.get("modes"):
                for m in inv["modes"]:
                    payment_modes[m.mode_of_payment] += flt(m.amount)

        # From Payment Entries (Receive)
        for p in pms:
            if p.mode_of_payment:
                payment_modes[p.mode_of_payment] += flt(p.paid_amount)

        # From Transfers (still record mode)
        for t in trs:
            if t.mode_of_payment:
                payment_modes[t.mode_of_payment] += flt(t.paid_amount)

        report[owner] = {
            "sales_invoices": invs,
            "payments": pms,
            "transfers": trs,
            "expenses": exps,
            "payment_modes": dict(payment_modes),   # converted to dict
            "totals": {
                "total_pos_sales": total_pos_sales,
                "total_credit_outstanding": total_credit_outstanding,
                "total_sales_overall": total_sales_overall,
                "total_received": total_received,
                "total_cash_at_hand": total_cash_at_hand,
                "total_banked": total_banked,
                "total_expenses": total_expenses,
                "balance_at_hand": balance_at_hand
            }
        }

    return {
        "from_date": from_date,
        "to_date": to_date,
        "report_by_owner": report
    }

@frappe.whitelist()
def create_internal_transfer(
    posting_date,
    mode_of_payment,
    reference_no=None,
    reference_date=None,
    paid_amount=0
):
    """
    Create an Internal Transfer Payment Entry.
    'paid_to' is automatically picked from the first default_account in the Mode of Payment child table.
    """

    if not (posting_date and mode_of_payment and paid_amount):
        frappe.throw(_("Missing required fields"))

    # Fetch MOP document
    mop = frappe.get_doc("Mode of Payment", mode_of_payment)

    if not mop.accounts or len(mop.accounts) == 0:
        frappe.throw(_("Selected Mode of Payment does not have any linked accounts in its child table"))

    # Pick the first default_account from the child table
    paid_to = mop.accounts[0].default_account

    if not paid_to:
        frappe.throw(_("The selected Mode of Payment child entry does not have a default_account set"))

    # Create Payment Entry
    payment_entry = frappe.new_doc("Payment Entry")
    payment_entry.payment_type = "Internal Transfer"
    payment_entry.posting_date = posting_date
    payment_entry.cost_center = "Main - AEL"  # can be made dynamic
    payment_entry.paid_from = "1110 - Cash - AEL"  # can be made dynamic
    payment_entry.paid_to = paid_to
    payment_entry.mode_of_payment = mode_of_payment
    payment_entry.reference_no = reference_no
    payment_entry.reference_date = reference_date
    payment_entry.paid_amount = paid_amount
    payment_entry.received_amount = paid_amount

    # Save and submit
    payment_entry.flags.ignore_permissions = True
    payment_entry.insert()
    payment_entry.submit()

    frappe.msgprint(_(f"Internal Transfer {payment_entry.name} created successfully"))

    return {
        "payment_entry_name": payment_entry.name,
        "paid_to": paid_to,
        "mode_of_payment": mode_of_payment
    }
