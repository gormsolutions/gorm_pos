import frappe
from frappe.utils import get_datetime, flt
from frappe.utils import now_datetime, getdate, flt
from frappe import _
from frappe.utils import flt, get_datetime

@frappe.whitelist()
def fetch_pos_closing_data(pos_profile, company, user, start_date, end_date, pos_opening_entry=None):
    result = {
        "pos_transactions": [],
        "payment_reconciliation": [],
        "grand_total": 0.0,
        "net_total": 0.0,
        "total_quantity": 0
    }

    if not start_date or not end_date:
        frappe.throw("Please set both Period Start Date and Period End Date.")

    start_date = get_datetime(start_date).date()
    end_date = get_datetime(end_date).date()

    filters = {
        "posting_date": ["between", [start_date, end_date]],
        "docstatus": 1,
        "pos_profile": pos_profile,
        "company": company,
        "owner": user,
    }

    invoices = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=["name", "posting_date", "grand_total", "net_total", "customer"]
    )

    invoice_names = [inv.name for inv in invoices]

    for inv in invoices:
        result["pos_transactions"].append({
            "customer": inv.customer,
            "pos_invoice": inv.name,
            "posting_date": inv.posting_date,
            "grand_total": flt(inv.grand_total)
        })
        result["grand_total"] += flt(inv.grand_total)
        result["net_total"] += flt(inv.net_total)

    if invoice_names:
        qty = frappe.db.sql("""
            SELECT SUM(qty) FROM `tabSales Invoice Item`
            WHERE parent IN %s
        """, (tuple(invoice_names),))[0][0] or 0
        result["total_quantity"] = qty
        
    

    # Always try to fetch the latest POS Opening Entry for that user, profile, and company
    try:
        if not pos_opening_entry:
            pos_opening_entry = frappe.db.get_value(
                "POS Opening Entry",
                {
                    "user": user,
                    "pos_profile": pos_profile,
                    "company": company,
                    "docstatus": 1
                },
                "name",
                order_by="creation desc"
            )

        if pos_opening_entry:
            opening = frappe.get_doc("POS Opening Entry", pos_opening_entry)
            for d in opening.balance_details:
                mop = d.mode_of_payment
                opening_amt = flt(d.opening_amount)

                sales_total = frappe.db.sql("""
                    SELECT SUM(amount) FROM `tabSales Invoice Payment`
                    WHERE parent IN %s AND mode_of_payment = %s
                """, (tuple(invoice_names), mop))[0][0] or 0.0

                expected = opening_amt + sales_total

                result["payment_reconciliation"].append({
                    "mode_of_payment": mop,
                    "opening_amount": opening_amt,
                    "expected_amount": expected,
                    "closing_amount": expected,
                    "difference": 0.0
                })

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "POS Closing Fetch Error")

    return result

@frappe.whitelist()
def create_my_pos_opening_entry(opening_amounts=None):
    """
    Create, save and submit a POS Opening Entry for the logged-in user.
    Ensures only one opening entry per user per day.
    """
    user = frappe.session.user
    today = getdate()

    # Check if an entry already exists
    existing_entry = frappe.db.get_value(
        "POS Opening Entry",
        {"user": user, "posting_date": today, "docstatus": 1},
        "name"
    )
    if existing_entry:
        return {
            "message": f"An opening entry already exists for user {user} on {today}.",
            "name": existing_entry,
            "exists": True
        }

    # Find POS Profile
    profile_link = frappe.get_all(
        "POS Profile User",
        filters={
            "user": user,
            "parenttype": "POS Profile",
            "parentfield": "applicable_for_users"
        },
        fields=["parent as pos_profile"],
        limit=1
    )
    if not profile_link:
        frappe.throw(f"User {user} is not assigned to any POS Profile.")

    pos_profile = profile_link[0].pos_profile

    # Load POS Profile
    profile_doc = frappe.get_doc("POS Profile", pos_profile)
    company = profile_doc.company or frappe.defaults.get_user_default("company")
    if not company:
        frappe.throw("No Company defined on the POS Profile or in your user defaults.")

    if not profile_doc.payments:
        frappe.throw(f"No Modes of Payment configured in POS Profile {pos_profile}.")

    # Parse amounts
    if isinstance(opening_amounts, str):
        import json
        opening_amounts = json.loads(opening_amounts)
    if not isinstance(opening_amounts, dict):
        frappe.throw("Please provide opening_amounts as a JSON object mapping mode_of_payment to amount.")

    # Create POS Opening Entry
    opening_entry = frappe.new_doc("POS Opening Entry")
    opening_entry.company = company
    opening_entry.pos_profile = pos_profile
    opening_entry.user = user
    opening_entry.posting_date = today
    opening_entry.period_start_date = now_datetime()
    opening_entry.set_posting_date = 1

    for pm in profile_doc.payments:
        mop = pm.mode_of_payment
        amt = flt(opening_amounts.get(mop, 0.0))
        opening_entry.append("balance_details", {
            "mode_of_payment": mop,
            "opening_amount": amt
        })

    opening_entry.insert()
    opening_entry.submit()

    return {
        "message": f"POS Opening Entry {opening_entry.name} created and submitted.",
        "name": opening_entry.name,
        "exists": False
    }

@frappe.whitelist()
def create_pos_closing_entry(start_date=None, end_date=None, closing_amounts=None):
    """
    Create or update and insert/submit a POS Closing Shift linked to the specified POS Opening Entry.
    - start_date, end_date: Period for aggregation.
    - closing_amounts: JSON string or dict of {mode_of_payment: closing_amount}.
    Returns a payload with opening_shift, pos_transactions, payment_reconciliation, totals, and closing_shift.
    """
    # 1) Validate & parse inputs
    if not (start_date and end_date):
        frappe.throw("Please set both Period Start Date and Period End Date.")
    start = get_datetime(start_date).date()
    end = get_datetime(end_date).date()
    
    from frappe.utils import nowdate
    today = nowdate()

    # Parse closing_amounts safely
    try:
        closing_amounts = frappe.parse_json(closing_amounts) if closing_amounts else {}
    except Exception:
        closing_amounts = {}
    if not isinstance(closing_amounts, dict):
        closing_amounts = {}

    # 2) Resolve user, profile, and company
    user = frappe.session.user

    # Get the POS Profile for the user
    profile_link = frappe.get_all(
        "POS Profile User",
        filters={"user": user, "parenttype": "POS Profile", "parentfield": "applicable_for_users"},
        fields=["parent as pos_profile"],
        limit=1
    )
    if not profile_link:
        frappe.throw(f"User {user} is not assigned to any POS Profile.")
    pos_profile = profile_link[0].pos_profile

    profile_doc = frappe.get_doc("POS Profile", pos_profile)
    company = profile_doc.company or frappe.defaults.get_user_default("company")
    if not company:
        frappe.throw("No Company defined on the POS Profile or in your user defaults.")
    if not profile_doc.payments:
        frappe.throw(f"No Modes of Payment configured on POS Profile {pos_profile}.")

    # 3) Fetch the latest POS Opening Entry for the user
    latest_opening = frappe.get_all(
        "POS Opening Entry",
        filters={
            "user": user,
            "pos_profile": pos_profile,
            "company": company,
            "docstatus": 1,
            "status": "Open"
        },
        fields=["name"],
        order_by="creation desc",
        limit=1
    )
    if not latest_opening:
        frappe.throw(f"No open POS Opening Entry found for user {user}.")
    pos_opening_entry = latest_opening[0].name
    opening = frappe.get_doc("POS Opening Entry", pos_opening_entry)

    # 4) Gather POS transactions & totals
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            # "posting_date": ["between", [start, end]],
            "posting_date": ["between", [today, today]],
            "docstatus": 1,
            "pos_profile": pos_profile,
            "company": company,
            "owner": user
        },
        fields=["name", "posting_date", "grand_total", "net_total", "customer"]
    )
    invoice_names = [inv.name for inv in invoices]

    pos_transactions = []
    grand_total = flt(0)
    net_total = flt(0)
    for inv in invoices:
        pos_transactions.append({
            "customer": inv.customer,
            "pos_invoice": inv.name,
            "posting_date": inv.posting_date,
            "grand_total": flt(inv.grand_total)
        })
        grand_total += flt(inv.grand_total)
        net_total += flt(inv.net_total)

    total_quantity = frappe.db.sql(
        """
        SELECT SUM(qty) FROM `tabSales Invoice Item`
        WHERE parent IN %s
        """, (tuple(invoice_names),)
    )[0][0] or 0 if invoice_names else 0

    # 5) Build payment reconciliation lines
    payment_reconciliation = []
    for detail in opening.balance_details:
        mop = detail.mode_of_payment
        opening_amt = flt(detail.opening_amount)
        sales_total = flt(frappe.db.sql(
            """
            SELECT SUM(amount) FROM `tabSales Invoice Payment`
            WHERE parent IN %s AND mode_of_payment = %s
            """, (tuple(invoice_names), mop)
        )[0][0] or 0.0)
        expected = opening_amt + sales_total
        user_closing_amt = flt(closing_amounts.get(mop, expected))
        difference = user_closing_amt - expected
        payment_reconciliation.append({
            "mode_of_payment": mop,
            "opening_amount": opening_amt,
            "expected_amount": expected,
            "closing_amount": user_closing_amt,
            "difference": difference
        })

    # 6) Create or update Closing Shift
    existing = frappe.db.get_value(
        "POS Closing Shift",
        {"pos_opening_entry": pos_opening_entry, "docstatus": ["<", 2]},
        "name"
    )
    if existing:
        closing_entry = frappe.get_doc("POS Closing Shift", existing)
        closing_entry.set("pos_transactions", [])
        closing_entry.set("payment_reconciliation", [])
    else:
        closing_entry = frappe.new_doc("POS Closing Shift")
        closing_entry.pos_opening_entry = pos_opening_entry

    closing_entry.update({
        "company": company,
        "pos_profile": pos_profile,
        "user": user,
        "period_start_date": start,
        "period_end_date": end,
        "grand_total": grand_total,
        "net_total": net_total,
        "total_quantity": total_quantity
    })

    for rec in payment_reconciliation:
        closing_entry.append("payment_reconciliation", rec)
    for txn in pos_transactions:
        closing_entry.append("pos_transactions", txn)

    if existing:
        closing_entry.save()
    else:
        closing_entry.insert()
    # Optional: closing_entry.submit()

    # 7) Return full payload
    return {
        "opening_shift": opening.as_dict(),
        "pos_transactions": pos_transactions,
        "payment_reconciliation": payment_reconciliation,
        "grand_total": grand_total,
        "net_total": net_total,
        "total_quantity": total_quantity,
        "closing_shift": closing_entry.as_dict()
    }

@frappe.whitelist()
def get_permitted_mop():
    user = frappe.session.user

    # 1) Find the POS Profile via the POS Profile User child doctype
    profile_link = frappe.get_all(
        "POS Profile User",
        filters={
            "user": user,
            "parenttype": "POS Profile",
            "parentfield": "applicable_for_users"
        },
        fields=["parent as pos_profile"],
        limit=1
    )
    if not profile_link:
        frappe.throw(f"User {user} is not assigned to any POS Profile.")

    pos_profile = profile_link[0].pos_profile

    # 2) Load the POS Profile and determine company
    profile_doc = frappe.get_doc("POS Profile", pos_profile)
    company = profile_doc.company or frappe.defaults.get_user_default("company")
    if not company:
        frappe.throw("No Company defined on the POS Profile or in your user defaults.")

    # 3) Ensure there are payment methods configured
    if not profile_doc.payments:
        frappe.throw(f"No Modes of Payment configured in POS Profile {pos_profile}.")

    # 4) Collect all modes of payment
    mops = [pm.mode_of_payment for pm in profile_doc.payments]

    return {
        "mops": mops
    }

@frappe.whitelist()
def check_shift():
    """
    Return the status of the POS Opening Entry for the current user today.
    If not found, return a default status message.
    """
    user = frappe.session.user
    today = getdate()

    entry_name = frappe.db.get_value(
        "POS Opening Entry",
        {
            "user": user,
            "posting_date": today,
            "docstatus": 1
        },
        "name"
    )

    if entry_name:
        status = frappe.db.get_value("POS Opening Entry", entry_name, "status")
        return {
            "exists": True,
            "status": status
        }
    else:
        return {
            "exists": False,
            "status": "No Shift found"
        }
