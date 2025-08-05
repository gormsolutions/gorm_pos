import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime, nowdate
from frappe.utils.data import flt

@frappe.whitelist(allow_guest=True)
def get_customer_details(limit, offset, search=None, last_sync=None):
    try:
        limit = int(limit)
        offset = int(offset)
        current_user = frappe.session.user

        # Step 1: Get default POS profile via raw SQL
        result = frappe.db.sql("""
            SELECT ppu.parent
            FROM `tabPOS Profile User` ppu
            JOIN `tabPOS Profile` pp ON pp.name = ppu.parent
            WHERE ppu.user = %s AND ppu.default = 1 AND pp.disabled = 0
            LIMIT 1
        """, (current_user,), as_dict=0)

        if not result:
            frappe.throw(_("No active POS Profile found for the user."))

        pos_profile = result[0][0]

        # Step 2: Get company from POS Profile (via raw SQL)
        company_row = frappe.db.sql("""
            SELECT company
            FROM `tabPOS Profile`
            WHERE name = %s
            LIMIT 1
        """, (pos_profile,), as_dict=1)

        if not company_row:
            frappe.throw(_("Company not found for POS Profile."))

        company = company_row[0]["company"]

        # Step 3: Build filters
        conditions = ["disabled = 0", "posa_referral_company = %s"]
        params = [company]

        if search:
            search = search.strip()
            like = f"%{search}%"
            conditions.append("(customer_name LIKE %s OR REPLACE(mobile_no, ' ', '') LIKE REPLACE(%s, ' ', ''))")
            params.extend([like, like])

        if last_sync:
            try:
                last_sync_dt = get_datetime(last_sync)
                if last_sync_dt and last_sync_dt <= now_datetime():
                    conditions.append("(creation >= %s OR modified >= %s)")
                    params.extend([last_sync_dt, last_sync_dt])
                else:
                    return []
            except Exception as e:
                frappe.log_error(f"Invalid last_sync: {last_sync} | Error: {e}", "get_customer_details")
                return []

        params.extend([limit, offset])

        # Step 4: Query Customer
        customers = frappe.db.sql(f"""
            SELECT name, customer_name, mobile_no, email_id, creation, modified
            FROM `tabCustomer`
            WHERE {" AND ".join(conditions)}
            ORDER BY modified DESC
            LIMIT %s OFFSET %s
        """, params, as_dict=True)

        # Step 5: Loyalty Enrichment
        enriched = []
        for customer in customers:
            summary = get_loyalty_summary_internal_sql(customer["name"])
            customer.update(summary)
            enriched.append(customer)

        return enriched

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_customer_details failed")
        return {
            "status": "error",
            "message": _("Failed to retrieve customer list"),
            "error": str(e),
        }


@frappe.whitelist(allow_guest=True)
def get_loyalty_summary_internal_sql(customer):
    # Step 1: Get all loyalty point entries (non-expired)
    entries = frappe.db.sql("""
        SELECT loyalty_points, loyalty_program
        FROM `tabLoyalty Point Entry`
        WHERE customer = %s AND expiry_date >= %s
    """, (customer, nowdate()), as_dict=True)

    earned, redeemed = 0, 0
    program = None

    for row in entries:
        points = flt(row.loyalty_points)
        if points > 0:
            earned += points
        elif points < 0:
            redeemed += points
        if not program and row.loyalty_program:
            program = row.loyalty_program

    remaining = earned + redeemed
    conversion_rate = redeemed_value = remaining_value = 0.0

    if program:
        rate_data = frappe.db.sql("""
            SELECT conversion_factor
            FROM `tabLoyalty Program`
            WHERE name = %s
            LIMIT 1
        """, (program,), as_dict=True)
        if rate_data:
            conversion_rate = flt(rate_data[0]["conversion_factor"])
            redeemed_value = abs(redeemed) * conversion_rate
            remaining_value = remaining * conversion_rate

    return {
        "loyalty_program": program,
        "earned_points": earned,
        "redeemed_points": abs(redeemed),
        "remaining_points": remaining,
        "conversion_rate": conversion_rate,
        "redeemed_value": redeemed_value,
        "remaining_value": remaining_value,
    }
