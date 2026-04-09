# promotion.py
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, flt

class Promotion(Document):
    def validate(self):
        if not self.start_date or not self.end_date:
            frappe.throw("Start Date and End Date are required")
        if self.end_date < self.start_date:
            frappe.throw("End Date cannot be before Start Date")

# Hook function to apply promotions on Sales Invoice
@frappe.whitelist()
def apply_promotions(doc, method=None):
    doc = frappe.get_doc(doc) if isinstance(doc, str) else doc
    active_promos = frappe.get_all("Promotion", filters={
        "enabled": 1,
        "start_date": ["<=", nowdate()],
        "end_date": [">=", nowdate()]
    }, fields=["name"])

    for promo in active_promos:
        promo_doc = frappe.get_doc("Promotion", promo.name)

        # Skip if channel or store do not match
        if promo_doc.channel and promo_doc.channel != doc.get("channel"):
            continue
        if promo_doc.store and promo_doc.store != doc.get("pos_profile"):
            continue

        # Skip if redemption limits are exceeded
        if promo_doc.max_redemptions and promo_doc.current_redemptions >= promo_doc.max_redemptions:
            continue
        if promo_doc.max_total_discount and promo_doc.current_discount >= promo_doc.max_total_discount:
            continue

        total_discount_given = 0

        for rule in promo_doc.promotion_items:
            for item in doc.items:
                match_item = rule.item_code == item.item_code if rule.item_code else True
                match_group = rule.item_group == item.item_group if rule.item_group else True

                if match_item and match_group:
                    if rule.min_qty and item.qty < rule.min_qty:
                        continue
                    if rule.discount_percent:
                        item.discount_percentage = rule.discount_percent
                        discount_amount = (rule.discount_percent / 100) * item.rate * item.qty
                        total_discount_given += discount_amount
                    if rule.gift_item:
                        doc.append("items", {
                            "item_code": rule.gift_item,
                            "qty": rule.gift_qty or 1,
                            "rate": 0,
                            "is_free_item": 1
                        })

        # Apply amount-off discounts from parent
        if promo_doc.type == "Amount Off Discount" and flt(doc.grand_total) >= flt(promo_doc.minimum_spend):
            discount = flt(promo_doc.discount_amount)
            doc.additional_discount_percentage = (discount / flt(doc.grand_total)) * 100
            total_discount_given += discount

        # Track redemptions and discount total
        if total_discount_given > 0:
            frappe.db.set_value("Promotion", promo_doc.name, {
                "current_redemptions": promo_doc.current_redemptions + 1,
                "current_discount": promo_doc.current_discount + total_discount_given
            })
