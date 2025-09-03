import frappe
from frappe import _
from frappe.utils import flt

@frappe.whitelist(allow_guest=False)
def get_vehicle_data(filters=None):
    """
    GET /api/method/your_app.api.vehicle_data.get_vehicle_data
    Query-string example:
        ?from_date=2024-01-01&to_date=2024-12-31&vehicle=MH-01-AB-1234
    Or fetch all:
        /api/method/your_app.api.vehicle_data.get_vehicle_data
    Returns:
        [
          {
            "vehicle": "MH-01-AB-1234",
            "make": "Toyota",
            "model": "Innova",
            "driver_name": "John Doe",
            "employee_name": "Jane Smith",
            "service_expense": 1250.0
          },
          ...
        ]
    """
    filters = frappe._dict(filters or frappe.local.form_dict)
    data = get_vehicle_log_data(filters)
    return data


# ---------------  private helpers ---------------
def get_vehicle_log_data(filters):
    conditions, values = get_conditions(filters)

    query = """
        SELECT
            vhcl.license_plate as vehicle,
            vhcl.make,
            vhcl.model,
            vhcl.custom_driver,
            vhcl.location,
            log.name as log_name,
            log.odometer,
            log.date,
            log.employee,
            log.fuel_qty,
            log.price as fuel_price,
            log.fuel_qty * log.price as fuel_expense
        FROM `tabVehicle` vhcl, `tabVehicle Log` log
        WHERE vhcl.license_plate = log.license_plate
          AND log.docstatus = 1
    """

    # only add date filter if both are provided
    if filters.get("from_date") and filters.get("to_date"):
        query += " AND log.date BETWEEN %(start_date)s AND %(end_date)s"

    query += f" {conditions} ORDER BY log.date"

    data = frappe.db.sql(query, values, as_dict=1)

    for row in data:
        # Service expense
        row["service_expense"] = get_service_expense(row.log_name)

        # Driver name (from Driver doctype, assume field full_name exists)
        row["driver_name"] = None
        if row.get("custom_driver"):
            row["driver_name"] = frappe.db.get_value("Driver", row.custom_driver, "full_name")

        # Employee name (from Employee doctype, assume field employee_name exists)
        row["employee_name"] = None
        if row.get("employee"):
            row["employee_name"] = frappe.db.get_value("Employee", row.employee, "employee_name")

    return data


def get_conditions(filters):
    conditions = ""
    values = {}

    # add dates to dict only if present
    if filters.get("from_date") and filters.get("to_date"):
        values["start_date"] = filters.get("from_date")
        values["end_date"] = filters.get("to_date")

    if filters.get("employee"):
        conditions += " AND log.employee = %(employee)s"
        values["employee"] = filters.employee

    if filters.get("vehicle"):
        conditions += " AND vhcl.license_plate = %(vehicle)s"
        values["vehicle"] = filters.vehicle

    return conditions, values


def get_period_dates(filters):
    if filters.get("filter_based_on") == "Fiscal Year" and filters.get("fiscal_year"):
        fy = frappe.db.get_value(
            "Fiscal Year",
            filters.fiscal_year,
            ["year_start_date", "year_end_date"],
            as_dict=True,
        )
        return fy.year_start_date, fy.year_end_date
    return filters.get("from_date"), filters.get("to_date")


def get_service_expense(logname):
    amount = frappe.db.sql(
        """
        SELECT SUM(expense_amount)
        FROM `tabVehicle Service`
        WHERE parent = %s
        """,
        logname,
    )
    return flt(amount[0][0]) if amount and amount[0][0] else 0.0
