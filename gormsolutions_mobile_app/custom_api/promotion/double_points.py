import frappe
from frappe.utils import today, flt, add_days, cint
from datetime import datetime

def get_today_mmdd():
    return datetime.strptime(today(), "%Y-%m-%d").strftime("%m-%d")

def is_customer_special_day(customer, special_type):
    """Check if today is customer's birthday or anniversary"""
    cust = frappe.get_doc("Customer", customer)
    today_mmdd = get_today_mmdd()

    if special_type == "Birthday":
        dob = cust.get("custom_date_of_birth")
        dob_mmdd = datetime.strptime(dob, "%Y-%m-%d").strftime("%m-%d") if dob else None
        return today_mmdd == dob_mmdd

    elif special_type == "Anniversary":
        anniv = cust.get("custom_anniversary_date")
        anniv_mmdd = datetime.strptime(anniv, "%Y-%m-%d").strftime("%m-%d") if anniv else None
        return today_mmdd == anniv_mmdd

    return False

def get_active_campaign_rules(company, types=["Birthday", "Anniversary"]):
    return frappe.get_all("Campaign Rule",
        filters={
            "type": ["in", types],
            "is_active": 1,
            "company": company
        },
        fields=["name", "type", "reward_type"]
    )

def get_campaign_free_items(campaign_name):
    return frappe.get_all("Free Item Promotion item",
        filters={"parent": campaign_name},
        fields=["free_item", "free_qty_per_main_qty"]
    )

def is_double_points_day(invoice_date):
    return frappe.db.exists("Double Points Day", {
        "date": invoice_date,
        "is_active": 1
    })

def get_loyalty_points(doc):
    program = frappe.get_doc("Loyalty Program", doc.loyalty_program)
    collection_factor = 1.0
    if program.collection_rules:
        rule = program.collection_rules[0]
        collection_factor = flt(rule.collection_factor or 1.0)

    total_spent = flt(doc.base_grand_total)

    if collection_factor <= 0:
        return 0

    return round(total_spent / collection_factor, 2)

def apply_special_day_rewards(doc, method):
    if not doc.customer or not doc.loyalty_program:
        return

    campaigns = get_active_campaign_rules(doc.company)
    if not campaigns:
        return

    for campaign in campaigns:
        if not is_customer_special_day(doc.customer, campaign.type):
            continue

        # Handle Free Item Reward
        if campaign.reward_type == "Free Item":
            items = get_campaign_free_items(campaign.name)
            for item in items:
                if any(i.item_code == item.free_item for i in doc.items):
                    continue
                doc.append("items", {
                    "item_code": item.free_item,
                    "qty": item.free_qty_per_main_qty or 1,
                    "rate": 0,
                    "amount": 0,
                    "is_free_item": 1,
                    "item_name": f"🎁 {campaign.type} Gift - {item.free_item}",
                    "description": f"Free {campaign.type.lower()} item from campaign",
                    "uom": "Nos"
                })

        # Handle Double Points Reward
        elif campaign.reward_type == "Double Points":
            # Check if today is a double points day (your custom logic)
            if not is_double_points_day(doc.posting_date):
                continue

            loyalty_points = get_loyalty_points(doc)
            if not loyalty_points:
                frappe.msgprint("No loyalty points calculated from the loyalty program.")
                continue

            program = frappe.get_doc("Loyalty Program", doc.loyalty_program)
            expiry_days = cint(program.expiry_duration) if program.expiry_duration else 365
            expiry_date = add_days(doc.posting_date, expiry_days)

            entry = frappe.new_doc("Loyalty Point Entry")
            entry.customer = doc.customer
            entry.loyalty_program = doc.loyalty_program
            entry.invoice_type = "Sales Invoice"
            entry.transaction_name = doc.name
            entry.invoice = doc.name
            entry.posting_date = doc.posting_date
            entry.loyalty_points = loyalty_points
            entry.purchase_amount = doc.loyalty_points
            entry.expiry_date = expiry_date
            entry.company = doc.company
            entry.remarks = f"🎉 {campaign.type} Double Points Bonus"

            entry.insert(ignore_permissions=True)
            entry.submit()

            frappe.msgprint(f"✅ {campaign.type} Double Points: Bonus {loyalty_points} Loyalty Points awarded!")

    frappe.msgprint("🎉 Special day rewards applied from campaign(s).")
