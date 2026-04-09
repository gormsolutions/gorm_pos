import frappe
import json

@frappe.whitelist()
def get_custom_pricing_rules(filters=None):
    """
    Fetch active Custom Pricing Rules with optional filters.
    Returns only essential fields for performance and readability.
    """
    try:
        # Parse JSON string filters if passed as string
        if isinstance(filters, str):
            filters = json.loads(filters)

        # Default filters: only enabled selling rules
        base_filters = {"disable": 0, "selling": 1}
        if filters:
            base_filters.update(filters)

        # Fetch matching Custom Pricing Rules (minimal fields)
        rule_data = frappe.get_all(
            "Custom Pricing Rule",
            filters=base_filters,
            fields=[
                "name",
                "title",
                "company",
                "currency",
                "apply_on",
                "price_or_product_discount",
                "rate_or_discount",
                "discount_percentage",
                "discount_amount",
                "discount_account",
                "applicable_for",
                "customer",
                "valid_from",
                "valid_upto",
                "customer_group",
                "item_code",
            ],
            order_by="modified desc"
        )

        return {"data": rule_data}

    except Exception as e:
        frappe.log_error(message=str(e), title="Error Fetching Custom Pricing Rules")
        frappe.throw(f"Failed to fetch Custom Pricing Rules: {str(e)}")
