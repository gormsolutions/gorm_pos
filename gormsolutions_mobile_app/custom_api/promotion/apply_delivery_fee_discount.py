import frappe
from frappe.utils import today, flt

def apply_delivery_fee_discount(doc, method):
    if not doc.get("cost_center"):
        return

    today_date = today()

    # Get active discount for today's date and matching store
    discounts = frappe.get_all("Delivery Fee Discount",
        filters={
            "store": doc.cost_center,
            "from_date": ("<=", today_date),
            "to_date": (">=", today_date),
            "is_active": 1
        },
        order_by="discount_type desc"
    )

    if not discounts:
        return  # No applicable discount

    discount = frappe.get_doc("Delivery Fee Discount", discounts[0].name)

    if discount.discount_type == "Free Delivery":
        doc.custom_delivery_fee = 0
    elif discount.discount_type == "Flat Fee":
        doc.custom_delivery_fee = max(0, discount.discount_amount)


@frappe.whitelist()
def create_delivery_fee_journal_entry(doc, method):
    delivery_fee = flt(getattr(doc, "custom_delivery_fee", 0))

    if not delivery_fee or delivery_fee <= 0:
        return

    # Define your delivery fee account
    delivery_account = "Delivery Fee Income - WASP"  # Update to match your Chart of Accounts

    # Create Journal Entry
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = doc.posting_date
    je.company = doc.company
    je.remark = f"Delivery Fee booking for {doc.name}"

    # Debit: Customer (Receivable)
    je.append("accounts", {
        "account": doc.debit_to,
        "party_type": "Customer",
        "party": doc.customer,
        "debit_in_account_currency": delivery_fee,
        "reference_type": "Sales Invoice",
        "reference_name": doc.name
    })

    # Credit: Delivery Fee Income Account
    je.append("accounts", {
        "account": delivery_account,
        "credit_in_account_currency": delivery_fee
    })

    je.insert(ignore_permissions=True)
    je.submit()

    frappe.msgprint(f"✅ Delivery Fee of ₦{delivery_fee} posted via Journal Entry {je.name}")
