import frappe
from frappe.utils import today
from frappe import _

@frappe.whitelist()
def get_loyalty_summary(customer):
    if not customer:
        return {"error": "Customer is required."}

    earned = 0
    redeemed = 0
    program = None

    # Fetch all loyalty entries for customer that are not expired
    entries = frappe.get_all(
        "Loyalty Point Entry",
        filters={
            "customer": customer,
            "expiry_date": [">=", today()]
        },
        fields=["loyalty_points", "loyalty_program"]
    )

    for entry in entries:
        points = entry.loyalty_points or 0

        if points > 0:
            earned += points
        elif points < 0:
            redeemed += points  # note: negative values
        if not program and entry.loyalty_program:
            program = entry.loyalty_program

    remaining = earned + redeemed  # redeemed is negative, so it's correct

    conversion_rate = 0
    redeemed_value = 0
    remaining_value = 0

    if program:
        loyalty_program = frappe.get_doc("Loyalty Program", program)
        conversion_rate = loyalty_program.conversion_factor or 0
        redeemed_value = abs(redeemed) * conversion_rate
        remaining_value = remaining * conversion_rate

    return {
        "customer": customer,
        "loyalty_program": program,
        "earned_points": earned,
        "redeemed_points": abs(redeemed),
        "remaining_points": remaining,
        "conversion_rate": conversion_rate,
        "redeemed_value": redeemed_value,
        "remaining_value": remaining_value
    }

@frappe.whitelist(allow_guest=True)
def get_customer_details(limit,offset,search=None):
    if search:
        filters=[
        ['disabled','=','No'] ,
        ['customer_name','like','%'+search+'%']]
    else:
        filters=[
        ['disabled','=','No']]

    customer_details = frappe.db.get_list('Customer',
    filters = filters,
    fields=['name','customer_name', 'mobile_no','email_id'],
    
    start=offset,
    page_length=limit
    )