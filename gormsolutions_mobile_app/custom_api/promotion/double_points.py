import frappe
from frappe.utils import flt, add_days, cint

def is_double_points_day(invoice_date):
    return frappe.db.exists("Double Points Day", {
        "date": invoice_date,
        "is_active": 1
    })

def get_best_collection_rule(program, amount):
    best_rule = None
    for rule in program.collection_rules:
        frappe.msgprint(f"Checking Tier: {rule.tier_name}, Min Spent: {rule.min_spent}")
        if flt(amount) >= flt(rule.min_spent):
            if not best_rule or flt(rule.min_spent) > flt(best_rule.min_spent):
                best_rule = rule

    if best_rule:
        frappe.msgprint(f"✅ Best Tier Selected: {best_rule.tier_name}")
    else:
        if program.collection_rules:
            best_rule = program.collection_rules[0]  # fallback to first rule (e.g. Bronze)
            frappe.msgprint(f"⚠️ No eligible tier found. Falling back to: {best_rule.tier_name}")
        else:
            frappe.msgprint("❌ No collection rules found at all.")
    return best_rule

def get_loyalty_points(doc):
    program = frappe.get_doc("Loyalty Program", doc.loyalty_program)
    total_spent = flt(doc.base_grand_total)

    best_rule = get_best_collection_rule(program, total_spent)

    if best_rule and flt(best_rule.collection_factor) > 0:
        loyalty_points = round(total_spent / flt(best_rule.collection_factor), 2)
        return loyalty_points, best_rule.tier_name
    else:
        return 0, ""

def double_loyalty_points_on_submit(doc, method):
    if not doc.loyalty_program or not doc.customer:
        frappe.msgprint("❌ Missing loyalty program or customer.")
        return

    if not is_double_points_day(doc.posting_date):
        frappe.msgprint("ℹ️ Not a Double Points Day.")
        return

    frappe.msgprint("✅ Double Points Day detected. Checking tiers...")

    loyalty_points, tier_name = get_loyalty_points(doc)
    if not loyalty_points:
        frappe.msgprint("❌ Loyalty points could not be calculated.")
        return

    program = frappe.get_doc("Loyalty Program", doc.loyalty_program)
    expiry_days = cint(program.expiry_duration) if program.expiry_duration else 365
    expiry_date = add_days(doc.posting_date, expiry_days)

    # Create the Loyalty Point Entry manually
    entry = frappe.new_doc("Loyalty Point Entry")
    entry.customer = doc.customer
    entry.loyalty_program = doc.loyalty_program
    entry.loyalty_program_tier = tier_name
    entry.invoice = doc.name
    entry.posting_date = doc.posting_date
    entry.loyalty_points = loyalty_points
    entry.purchase_amount = doc.base_grand_total
    entry.invoice_type = "Sales Invoice"
    entry.expiry_date = expiry_date
    entry.company = doc.company
    entry.remarks = "🎉 Double Points Day Bonus"

    entry.insert(ignore_permissions=True)
    entry.submit()

    frappe.msgprint(f"✅ {tier_name} Tier: Bonus {loyalty_points} Loyalty Points awarded via entry {entry.name}.")
