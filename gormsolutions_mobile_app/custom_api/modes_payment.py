import frappe

@frappe.whitelist()
def get_all_payment_modes():
    # Fetch all enabled modes of payment
    payment_modes = frappe.get_all(
        "Mode of Payment",  # The doctype where payment modes are stored
        filters={"enabled": 1},  # Filter to get only enabled modes of payment
        fields=["name"]  # You can add other fields as necessary
    )

    # If no payment modes found, return an empty list
    if not payment_modes:
        return []

    # Return the payment modes data
    return payment_modes

