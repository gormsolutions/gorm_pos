import frappe
from frappe.utils import flt, today, add_months

@frappe.whitelist()
def regenerate_single_schedule(asset_name):
    asset = frappe.get_doc("Asset", asset_name)

    # Check if Asset Depreciation Schedule already exists
    ads_list = frappe.get_all(
        "Asset Depreciation Schedule",
        filters={"asset": asset.name},
        pluck="name"
    )

    if not ads_list:
        # Create the parent Asset Depreciation Schedule
        schedule = frappe.get_doc({
            "doctype": "Asset Depreciation Schedule",
            "asset": asset.name,
            "company": asset.company,
            "start_date": asset.purchase_date or today(),
            "total_amount_to_depreciate": flt(asset.gross_purchase_amount) - flt(getattr(asset, "expected_value_after_useful_life", 0)),
            "depreciation_method": asset.depreciation_method,
            "depreciation_rate": flt(asset.rate_of_depreciation),
            "total_number_of_depreciations": flt(asset.total_number_of_depreciations) or 36,
            "daily_prorata_based": getattr(asset, "daily_prorata_based", 0),
            "shift_based": getattr(asset, "shift_based", 0),
            "frequency_of_depreciation": getattr(asset, "frequency_of_depreciation", 1),
            "expected_value_after_useful_life": getattr(asset, "expected_value_after_useful_life", 0)
        })
        schedule.insert()
        frappe.db.commit()
    else:
        schedule = frappe.get_doc("Asset Depreciation Schedule", ads_list[0])

    # Check which child entries already exist
    existing_dates = set(frappe.get_all(
        "Depreciation Schedule",
        filters={"parent": schedule.name},
        pluck="schedule_date"
    ))

    # Generate missing depreciation entries
    depreciation_amount = flt(schedule.total_amount_to_depreciate) / schedule.total_number_of_depreciations
    accumulated_amount = 0
    current_date = schedule.start_date

    for i in range(1, int(schedule.total_number_of_depreciations) + 1):
        if current_date in existing_dates:
            accumulated_amount += depreciation_amount
            current_date = add_months(current_date, schedule.frequency_of_depreciation)
            continue

        accumulated_amount += depreciation_amount
        child = frappe.get_doc({
            "doctype": "Depreciation Schedule",
            "parent": schedule.name,
            "parentfield": "depreciation_details",
            "parenttype": "Asset Depreciation Schedule",
            "schedule_date": current_date,
            "depreciation_amount": depreciation_amount,
            "accumulated_depreciation_amount": accumulated_amount,
            "shift": schedule.shift_based  # optional
        })
        child.insert()
        current_date = add_months(current_date, schedule.frequency_of_depreciation)

    schedule.reload()
    frappe.db.commit()
    return {"message": f"✅ Depreciation schedule regenerated for {asset.name}"}

import frappe

@frappe.whitelist()
def check_and_add_button(asset_name):
    """
    Return whether to show the 'Regenerate Depreciation Schedule' button
    """
    asset = frappe.get_doc("Asset", asset_name)

    # Example logic: show button only if asset has no depreciation entries
    ads_list = frappe.get_all(
        "Asset Depreciation Schedule",
        filters={"asset": asset.name},
        pluck="name"
    )

    has_entries = any(
        frappe.get_all("Depreciation Schedule", filters={"parent": ads}, limit=1)
        for ads in ads_list
    )

    return {"show_button": not has_entries}



    import frappe

# @frappe.whitelist()
# def get_assets_without_schedule_date(company=None):
#     if not company:
#         frappe.throw("Please provide a company")

#     return frappe.db.sql("""
#         SELECT DISTINCT
#             d.asset                                   AS asset_name,
#             d.depreciation_method,
#             d.frequency_of_depreciation,
#             d.total_number_of_depreciations,
#             d.expected_value_after_useful_life
#         FROM `tabAsset Depreciation Schedule` d
#         LEFT JOIN `tabDepreciation Schedule` ds
#                ON ds.parent = d.name
#         INNER JOIN `tabAsset` a
#                ON a.name = d.asset
#         WHERE ds.name IS NULL              -- <-- NO child rows
#           AND d.docstatus = 1
#           AND d.company = %(company)s
#           AND a.docstatus = 1
#           AND a.asset_owner_company = %(company)s
#           AND a.status != 'Fully Depreciated'
#         ORDER BY d.creation DESC
#     """, {"company": company}, as_dict=True)

import frappe
from dateutil.relativedelta import relativedelta
from datetime import date

@frappe.whitelist()
def get_assets_without_schedule_date(company=None):
    if not company:
        frappe.throw("Please provide a company")

    raw = frappe.db.sql("""
        SELECT
            d.asset                                   AS asset_name,
            d.depreciation_method,
            d.frequency_of_depreciation,
            d.total_number_of_depreciations,
            d.expected_value_after_useful_life,
            a.purchase_date,
            a.available_for_use_date
        FROM `tabAsset Depreciation Schedule` d
        LEFT JOIN `tabDepreciation Schedule` ds
               ON ds.parent = d.name
        INNER JOIN `tabAsset` a
               ON a.name = d.asset
        WHERE ds.name IS NULL              -- no child rows
          AND d.docstatus = 1
          AND d.company = %(company)s
          AND a.docstatus = 1
          AND a.asset_owner_company = %(company)s
          AND a.status != 'Fully Depreciated'
        ORDER BY d.creation DESC
    """, {"company": company}, as_dict=True)

    # enrich with Months Remaining
    today = date.today()
    for row in raw:
        start = row.available_for_use_date or row.purchase_date
        if start:
            months_elapsed = relativedelta(today, start).months + relativedelta(today, start).years * 12
            months_elapsed = max(months_elapsed, 0)
            months_remaining = max(row.total_number_of_depreciations * row.frequency_of_depreciation - months_elapsed, 0)
        else:
            months_remaining = row.total_number_of_depreciations * row.frequency_of_depreciation
        row.months_remaining = months_remaining

    return raw