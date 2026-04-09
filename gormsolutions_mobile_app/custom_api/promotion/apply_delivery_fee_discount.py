import frappe
from frappe.utils import today, flt

def apply_delivery_fee_discount(doc, method):
    """
    Apply delivery fee discount based on the cost_center (store)
    and today's active discount rules.
    """
    if not doc.get("cost_center"):
        return

    today_date = today()

    # Get active discounts for today and the store (cost_center)
    discounts = frappe.get_all(
        "Delivery Fee Discount",
        filters={
            "store": doc.cost_center,
            "from_date": ["<=", today_date],
            "to_date": [">=", today_date],
            "is_active": 1,
            "company": doc.company,
        },
        order_by="discount_type desc",
        limit_page_length=1,
    )

    if not discounts:
        return  # No discount applicable

    discount = frappe.get_doc("Delivery Fee Discount", discounts[0].name)

    if discount.discount_type == "Free Delivery":
        doc.custom_delivery_fee = 0
    elif discount.discount_type == "Flat Fee":
        doc.custom_delivery_fee = max(0, discount.discount_amount)
        frappe.db.commit()
    else:
        # Optional: handle other discount types if any
        pass


import frappe
from frappe.utils import flt

@frappe.whitelist()
def create_delivery_fee_journal_entry(doc, method):
    """
    Create a Journal Entry for the delivery fee after applying discount.
    """

    delivery_fee = flt(getattr(doc, "custom_delivery_fee", 0))
    if not delivery_fee or delivery_fee <= 0:
        return  # No fee to post

    # Get active discount based on posting_date and cost_center
    discounts = frappe.get_all(
        "Delivery Fee Discount",
        filters={
            "store": doc.cost_center,
            "from_date": ["<=", doc.posting_date],
            "to_date": [">=", doc.posting_date],
            "is_active": 1,
            "company": doc.company,
        },
        order_by="discount_type desc",
        limit_page_length=1,
    )

    if not discounts:
        frappe.throw("No active Delivery Fee Discount found for this document.")

    discount = frappe.get_doc("Delivery Fee Discount", discounts[0].name)

    # Debug: Log the delivery_account value
    frappe.log_error(f"Delivery Account found: {discount.delivery_account}", "Delivery Fee Discount Debug")

    delivery_account = discount.delivery_account

    # If delivery_account is missing, try fallback or throw
    if not delivery_account:
        # You can set a fallback account here if you want, else throw error
        # Example fallback (uncomment if needed):
        # delivery_account = "Sales - " + doc.company
        frappe.throw("Delivery Fee Discount does not have a Delivery Account set.")

    # Create Journal Entry doc
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = doc.posting_date
    je.company = discount.company  # Use company from discount doc
    je.remarks = f"Delivery Fee booking for {doc.name}"

    # Debit entry: Customer (Receivable)
    je.append("accounts", {
        "account": doc.debit_to,
        "party_type": "Customer",
        "party": doc.customer,
        "debit_in_account_currency": delivery_fee,
        "reference_type": doc.doctype,
        "reference_name": doc.name
    })

    # Credit entry: Delivery Fee Income Account
    je.append("accounts", {
        "account": delivery_account,
        "credit_in_account_currency": delivery_fee
    })

    je.insert(ignore_permissions=True)
    je.submit()

    frappe.msgprint(f"✅ Delivery Fee of ₦{delivery_fee} posted via Journal Entry {je.name}")
