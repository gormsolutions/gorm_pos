# import frappe
# from frappe.utils import now_datetime, today

# @frappe.whitelist()
# def create_vehicle_log_with_expense(payload=None):
#     """
#     Create a Vehicle Log and a Draft Expense Claim for Vehicle Expenses.
#     `payload` must be sent as JSON string or dict.
#     """
#     import json

#     if not payload:
#         frappe.throw("Payload is required")

#     if isinstance(payload, str):
#         payload = json.loads(payload)

#     # --- Mandatory fields ---
#     mandatory_fields = ["vehicle", "custom_driver_name", "employee", "odometer_reading"]
#     for field in mandatory_fields:
#         if field not in payload or payload[field] in (None, ""):
#             frappe.throw(f"Mandatory field missing: {field}")

#     vehicle_plate = payload["vehicle"]
#     employee = payload["employee"]
#     log_date = payload.get("log_date") or now_datetime()
#     service_details = payload.get("service_details", [])

#     # --- Fetch Vehicle safely ---
#     vehicle_doc_list = frappe.get_all("Vehicle", filters={"license_plate": vehicle_plate}, limit=1)
#     if not vehicle_doc_list:
#         frappe.throw(f"Vehicle with license plate {vehicle_plate} not found")
#     vehicle_doc = frappe.get_doc("Vehicle", vehicle_doc_list[0].name)

#     # --- Validate Odometer ---
#     odometer_reading = payload.get("odometer_reading")
#     if odometer_reading <= vehicle_doc.last_odometer:
#         frappe.throw(
#             f"Current Odometer Value should be greater than Last Odometer Value {vehicle_doc.last_odometer}"
#         )

#     # --- Create Vehicle Log ---
#     log = frappe.new_doc("Vehicle Log")
#     log.license_plate = vehicle_doc.license_plate
#     log.date = log_date
#     log.custom_driver_name = payload.get("custom_driver_name") or vehicle_doc.custom_driver
#     log.fuel_qty = payload.get("fuel_qty") or 0
#     log.fuel_rate = payload.get("fuel_rate") or 0
#     log.supplier = payload.get("supplier") or ""
#     log.invoice = payload.get("invoice") or ""
#     log.employee = employee
#     log.last_odometer = vehicle_doc.last_odometer
#     log.odometer = odometer_reading  # Use current_odometer field

#     # Append service details if any
#     for svc in service_details:
#         log.append("service_detail", {
#             "service_item": svc.get("service_item"),
#             "type": "Service",
#             "frequency": svc.get("frequency"),
#             "expense_amount": svc.get("expense_amount") or 0
#         })

#     log.insert(ignore_permissions=True)
#     log.submit()

#     # --- Create Draft Expense Claim ---
#     expense_claim = frappe.new_doc("Expense Claim")
#     expense_claim.employee = log.employee
#     expense_claim.expense_date = today()
#     expense_claim.company = frappe.defaults.get_global_default("company")
#     expense_claim.expense_approver = "martin@gmail.com"
#     expense_claim.vehicle_log = log.name  # Not linked to a vehicle_log

#     # Append expense rows BEFORE insert to avoid MandatoryError
#     for svc in service_details:
#         if svc.get("expense_amount"):
#             expense_claim.append("expenses", {
#                 "expense_type": "Vehicle Expenses",
#                 "description": svc.get("service_item"),
#                 "amount": svc.get("expense_amount"),
#                 "sanctioned_amount": svc.get("expense_amount")
#             })

#     expense_claim.insert(ignore_permissions=True)
#     expense_claim.save(ignore_permissions=True)

#     return {
#         "vehicle_log": log.name,
#         "expense_claim": expense_claim.name
#     }


import frappe
from frappe.utils import now_datetime, today

@frappe.whitelist()
def create_vehicle_log_with_expense(payload=None):
    import json

    if not payload:
        frappe.throw("Payload is required")

    if isinstance(payload, str):
        payload = json.loads(payload)

    # --- Mandatory fields ---
    mandatory_fields = ["vehicle", "custom_driver_name", "employee", "odometer_reading"]
    for field in mandatory_fields:
        if field not in payload or payload[field] in (None, ""):
            frappe.throw(f"Mandatory field missing: {field}")

    vehicle_plate = payload["vehicle"]
    employee = payload["employee"]
    log_date = payload.get("log_date") or now_datetime()
    service_details = payload.get("service_details", [])

    fuel_qty = payload.get("fuel_qty") or 0
    fuel_rate = payload.get("fuel_rate") or 0

    # --- Payment Fields --- payload.get("mode_of_payment") payload.get("payable_account")

    is_paid = int(payload.get("is_paid") or 0)
    mode_of_payment = "Cash" if is_paid else None
    payable_account = "2170 - Creditors - SD" if is_paid else None
    # --- Company & Cost Center ---
    company = frappe.defaults.get_global_default("company")
    default_cost_center = frappe.db.get_value("Company", company, "cost_center")

    cost_center = payload.get("cost_center") or default_cost_center
    if not cost_center:
        frappe.throw("Cost Center is required (set Company default or pass in payload)")

    # --- Fetch Vehicle ---
    vehicle_doc_list = frappe.get_all(
        "Vehicle", filters={"license_plate": vehicle_plate}, limit=1
    )
    if not vehicle_doc_list:
        frappe.throw(f"Vehicle with license plate {vehicle_plate} not found")

    vehicle_doc = frappe.get_doc("Vehicle", vehicle_doc_list[0].name)

    # --- Validate Odometer ---
    odometer_reading = payload.get("odometer_reading")
    if odometer_reading <= vehicle_doc.last_odometer:
        frappe.throw(
            f"Current Odometer Value should be greater than Last Odometer Value {vehicle_doc.last_odometer}"
        )

    # --- Create Vehicle Log ---
    log = frappe.new_doc("Vehicle Log")
    log.license_plate = vehicle_doc.license_plate
    log.date = log_date
    log.custom_driver_name = payload.get("custom_driver_name") or vehicle_doc.custom_driver
    log.fuel_qty = fuel_qty
    log.fuel_rate = fuel_rate
    log.supplier = payload.get("supplier") or ""
    log.invoice = payload.get("invoice") or ""
    log.employee = employee
    log.last_odometer = vehicle_doc.last_odometer
    log.odometer = odometer_reading

    for svc in service_details:
        log.append("service_detail", {
            "service_item": svc.get("service_item"),
            "type": "Service",
            "frequency": svc.get("frequency"),
            "expense_amount": svc.get("expense_amount") or 0
        })

    log.insert(ignore_permissions=True)
    log.submit()

    # --- Create Expense Claim ---
    expense_claim = frappe.new_doc("Expense Claim")
    expense_claim.employee = employee
    expense_claim.expense_date = today()
    expense_claim.company = company
    expense_claim.expense_approver = "martin@gmail.com"
    expense_claim.vehicle_log = log.name

    # --- FORCE APPROVAL ---
    expense_claim.approval_status = "Approved"

    has_expense = False

    # --- Fuel Expense ---
    if fuel_qty > 0 and fuel_rate > 0:
        fuel_amount = fuel_qty * fuel_rate
        expense_claim.append("expenses", {
            "expense_type": "Motor vehicle Fuel  Expenses",
            "description": f"Fuel - {fuel_qty} L @ {fuel_rate}",
            "amount": fuel_amount,
            "sanctioned_amount": fuel_amount,
            "cost_center": cost_center
        })
        has_expense = True

    # --- Service Expenses ---
    for svc in service_details:
        if svc.get("expense_amount"):
            expense_claim.append("expenses", {
                "expense_type": "Vehicle Expenses",
                "description": svc.get("service_item"),
                "amount": svc.get("expense_amount"),
                "sanctioned_amount": svc.get("expense_amount"),
                "cost_center": cost_center
            })
            has_expense = True

    if not has_expense:
        return {
            "vehicle_log": log.name,
            "expense_claim": None
        }

    # --- Insert Expense Claim ---
    expense_claim.insert(ignore_permissions=True)

    # --- Payment Handling ---
    if is_paid:
        if not mode_of_payment:
            frappe.throw("mode_of_payment is required when is_paid = 1")
        if not payable_account:
            frappe.throw("payable_account is required when is_paid = 1")

        expense_claim.is_paid = 1
        expense_claim.mode_of_payment = mode_of_payment
        expense_claim.payable_account = payable_account

    expense_claim.save(ignore_permissions=True)

    # --- SUBMIT (Creates GL Entries) ---
    expense_claim.submit()

    return {
        "vehicle_log": log.name,
        "expense_claim": expense_claim.name
    }
