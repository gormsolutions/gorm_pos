import frappe
from frappe import _
from frappe.utils import nowdate, getdate

@frappe.whitelist()
def fetch_user_coupons():
    current_user = frappe.session.user
    if not current_user:
        frappe.throw(_("No logged-in user found."))

    # ✅ Require default POS Profile
    result = frappe.db.sql("""
        SELECT ppu.parent
        FROM `tabPOS Profile User` ppu
        JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
        WHERE ppu.user = %s AND ppu.default = 1 AND pp.disabled = 0
        LIMIT 1
    """, (current_user,), as_dict=0)

    if not result:
        frappe.throw(f"User '{current_user}' must have an active default POS Profile assigned.")

    pos_profile = result[0][0]
    pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
    company = pos_profile_doc.company

    # Build filters
    filters = {"custom_disable":0,"custom_active":1}
    if company:
        filters["custom_company"] = company  # Filter by POS Profile company

    # Fetch coupon codes
    coupons = frappe.get_all(
        "Coupon Code",
        filters=filters,
        fields=[
            "name",
            "coupon_name",
            "coupon_type",
            "coupon_code",
            "custom_min_amt",
            "custom_max_amt",
            "custom_affected_item",
            "custom_on_customer",
            "custom_customer_group",
            "custom_company",
            "custom_discount_percent",
            "custom_discount_amount",
            "custom_discount_account",
            "valid_from",
            "valid_upto",
            "maximum_use",
            "used",
        ],
        order_by="valid_upto desc"
    )

    # Filter valid coupons using getdate()
    today = getdate(nowdate())
    valid_coupons = []
    for c in coupons:
        if (not c.get("valid_from") or getdate(c["valid_from"]) <= today) and \
           (not c.get("valid_upto") or getdate(c["valid_upto"]) >= today):
            valid_coupons.append(c)

    return valid_coupons

