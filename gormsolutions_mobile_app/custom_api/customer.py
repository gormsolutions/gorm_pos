import frappe

import frappe
from frappe.utils import today
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_customer_details(limit, offset, search=None):
    if search:
        filters = [
            ['disabled', '=', 'No'],
            ['customer_name', 'like', '%' + search + '%']
        ]
    else:
        filters = [['disabled', '=', 'No']]

    customer_list = frappe.db.get_list(
        'Customer',
        filters=filters,
        fields=['name', 'customer_name', 'mobile_no', 'email_id'],
        start=offset,
        page_length=limit
    )

    result = []

    for customer in customer_list:
        summary = get_loyalty_summary_internal(customer.name)
        customer.update(summary)
        result.append(customer)

    return result

def get_loyalty_summary_internal(customer):
    earned = 0
    redeemed = 0
    program = None

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
            redeemed += points
        if not program and entry.loyalty_program:
            program = entry.loyalty_program

    remaining = earned + redeemed

    conversion_rate = 0
    redeemed_value = 0
    remaining_value = 0

    if program:
        loyalty_program = frappe.get_doc("Loyalty Program", program)
        conversion_rate = loyalty_program.conversion_factor or 0
        redeemed_value = abs(redeemed) * conversion_rate
        remaining_value = remaining * conversion_rate

    return {
        "loyalty_program": program,
        "earned_points": earned,
        "redeemed_points": abs(redeemed),
        "remaining_points": remaining,
        "conversion_rate": conversion_rate,
        "redeemed_value": redeemed_value,
        "remaining_value": remaining_value
    }


import frappe
from frappe import _

import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def create_customer(
    customer_name,
    mobile_no,
    email_id=None,
    naming_series="CUST-.YYYY.-",
    customer_type="Individual",
    customer_group=None,
    custom_cost_center=None,
    territory=None
):
    try:
        current_user = frappe.session.user

        # Fetch cost centers allowed for user from User Permission where is_default=0
        cost_centers = frappe.get_all(
            'User Permission',
            filters={
                'user': current_user,
                'allow': 'Cost Center',
                'is_default': 0
            },
            fields=['for_value']
        )

        # If no non-default cost centers, fallback to default ones (is_default=1)
        if not cost_centers:
            cost_centers = frappe.get_all(
                'User Permission',
                filters={
                    'user': current_user,
                    'allow': 'Cost Center',
                    'is_default': 1
                },
                fields=['for_value']
            )

        # Pick first cost center from permissions if custom_cost_center not provided
        if not custom_cost_center:
            custom_cost_center = cost_centers[0]['for_value'] if cost_centers else None

        doc = frappe.new_doc('Customer')
        doc.naming_series = naming_series
        doc.customer_name = customer_name
        doc.customer = customer_name
        doc.mobile_no = mobile_no
        doc.customer_type = customer_type
        doc.customer_group = customer_group
        doc.custom_cost_center = custom_cost_center
        doc.territory = territory

        if email_id:
            doc.email_id = email_id

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Customer created successfully"),
            "customer_name": doc.name,
            "custom_cost_center": custom_cost_center
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Customer Creation Failed")
        return {
            "status": "error",
            "message": _("Failed to create customer"),
            "error": str(e)
        }


import frappe
from frappe import _

@frappe.whitelist()
def fetch_customer_metadata():
    try:
        # Fetch all Customer Groups
        customer_groups = frappe.get_all(
            "Customer Group",
            filters={"is_group": 0},
            fields=["name"]
        )

        # Fetch all Territories
        territories = frappe.get_all(
            "Territory",
            filters={"is_group": 0},
            fields=["name"]
        )

        return {
            "status": "success",
            "message": _("Customer metadata fetched successfully"),
            "data": {
                "customer_groups": [g.name for g in customer_groups],
                "territories": [t.name for t in territories]
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Fetch Customer Metadata Failed")
        return {
            "status": "error",
            "message": _("Failed to fetch customer metadata"),
            "error": str(e)
        }
