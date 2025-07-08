import frappe
from frappe.utils import today, flt
from datetime import datetime

def get_today_mmdd():
    return datetime.strptime(today(), "%Y-%m-%d").strftime("%m-%d")

def is_customer_special_day(customer, special_type):
    """Check if today matches the customer's birthday or anniversary"""
    cust = frappe.get_doc("Customer", customer)
    today_mmdd = get_today_mmdd()

    if special_type == "Birthday":
        dob = cust.get("custom_date_of_birth")
        if dob:
            dob_str = dob.strftime("%Y-%m-%d") if not isinstance(dob, str) else dob
            dob_mmdd = datetime.strptime(dob_str, "%Y-%m-%d").strftime("%m-%d")
            return today_mmdd == dob_mmdd

    elif special_type == "Anniversary":
        anniv = cust.get("custom_anniversary_date")
        if anniv:
            anniv_str = anniv.strftime("%Y-%m-%d") if not isinstance(anniv, str) else anniv
            anniv_mmdd = datetime.strptime(anniv_str, "%Y-%m-%d").strftime("%m-%d")
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

def add_special_day_free_items(doc, method):
    """Called on `before_save` to add free items for Birthday/Anniversary"""
    if not doc.customer:
        return

    campaigns = get_active_campaign_rules(doc.company)
    if not campaigns:
        return

    for campaign in campaigns:
        if campaign.reward_type != "Free Item":
            continue

        if not is_customer_special_day(doc.customer, campaign.type):
            continue

        items = get_campaign_free_items(campaign.name)
        for item in items:
            # Avoid duplicate entry
            if any(i.item_code == item.free_item for i in doc.items):
                continue

            item_details = frappe.get_doc("Item", item.free_item)

            # Get income_account from Item Defaults
            income_account = ""
            if item_details.item_defaults:
                income_account = item_details.item_defaults[0].income_account or ""

            doc.append("items", {
                "item_code": item_details.item_code,
                "item_name": item_details.item_name,
                "uom": item_details.stock_uom,
                "qty": item.free_qty_per_main_qty or 1,
                "conversion_factor": 1,
                "rate": 0,
                "amount": 0,
                "base_rate": 0,
                "base_amount": 0,
                "price_list_rate": 0,
                "income_account": income_account,
                "expense_account": "5222 - Discount Allowed - WASP",
                "description": "Free Item",
                "is_free_item": 1,
                "custom_free_item": 1,
                "cost_center": doc.cost_center
            })

def apply_special_day_loyalty_points(doc, method):
    """Called on `before_submit` to apply double loyalty points for Birthday/Anniversary"""
    if not doc.customer or not doc.loyalty_program:
        return

    campaigns = get_active_campaign_rules(doc.company)
    if not campaigns:
        return

    for campaign in campaigns:
        if campaign.reward_type != "Double Points":
            continue

        if not is_customer_special_day(doc.customer, campaign.type):
            continue

        program = frappe.get_doc("Loyalty Program", doc.loyalty_program)
        collection_factor = 1
        if program.collection_rules:
            rule = program.collection_rules[0]
            collection_factor = flt(rule.collection_factor or 1)

        loyalty_points = (flt(doc.base_grand_total) / collection_factor) * 2  # Double points

        entry = frappe.new_doc("Loyalty Point Entry")
        entry.customer = doc.customer
        entry.loyalty_program = doc.loyalty_program
        entry.transaction_type = "Sales Invoice"
        entry.transaction_name = doc.name
        entry.posting_date = doc.posting_date
        entry.loyalty_points = loyalty_points
        entry.company = doc.company
        entry.remarks = f"🎉 {campaign.type} Double Points Bonus"
        entry.insert(ignore_permissions=True)
        entry.submit()

        frappe.msgprint(f"🎉 {campaign.type} Bonus: {loyalty_points} double loyalty points awarded!")
