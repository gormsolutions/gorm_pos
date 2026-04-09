import frappe
from frappe.utils import nowdate

def apply_standard_percentage_discount(doc, method):
    """
    Hook into Sales Invoice, POS Invoice, or Sales Order validation to apply active percentage-based promotions.
    """
    today = nowdate()

    promotions = frappe.get_all(
        "Promotion",
        filters={
            "enabled": 1,
            "type": "Standard % Discount",
            "start_date": ["<=", today],
            "end_date": [">=", today],
            "store": doc.set_warehouse or doc.branch or doc.company
        },
        fields=["name", "discount_amount", "item_group", "max_total_discount_value", "current_discount_given"]
    )

    if not promotions:
        return

    for promo in promotions:
        discount_total = 0.0
        for item in doc.items:
            # Check if item belongs to promotion's item group
            item_doc = frappe.get_doc("Item", item.item_code)
            if item_doc.item_group == promo.item_group:
                # Apply % discount per item
                discount_percent = get_discount_percent(promo.name, item.item_code)
                if discount_percent:
                    original_rate = item.rate
                    discounted_rate = original_rate * (1 - (discount_percent / 100.0))
                    discount_total += (original_rate - discounted_rate) * item.qty
                    item.rate = discounted_rate
                    item.discount_percentage = discount_percent

        # Update current discount given
        if discount_total:
            promo_doc = frappe.get_doc("Promotion", promo.name)
            promo_doc.current_discount_given += discount_total
            promo_doc.save(ignore_permissions=True)

def get_discount_percent(promotion_name, item_code):
    """
    Fetch discount percent for a given item in the promotion's item table.
    """
    entry = frappe.db.get_value(
        "Promotion Item",
        {"parent": promotion_name, "item_code": item_code},
        "discount_percent"
    )
    return float(entry or 0)
