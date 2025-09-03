import frappe
from frappe.utils import now_datetime, today, get_datetime

@frappe.whitelist()
def create_delivery_trip_with_expense(driver, vehicle, employee, total_distance,
                                      departure_time=None, delivery_stops=None, expenses=None):
    """
    Create a Delivery Trip and automatically create a linked Expense Claim.

    Args:
        driver (str): Driver (Link to Driver)
        vehicle (str): Vehicle (Link to Vehicle)
        employee (str): Employee responsible for the trip
        total_distance (float): Total distance traveled
        departure_time (str, optional): Departure datetime (accepts DD-MM-YYYY or YYYY-MM-DD)
        delivery_stops (list, optional): List of stops as dicts
            [{customer, address, delivery_note, estimated_arrival}]
        expenses (list, optional): List of expense dicts
            [{expense_type, description, amount}]

    Returns:
        dict: { "delivery_trip": <name>, "expense_claim": <name> }
    """

    # --- Parse departure_time safely ---
    parsed_departure = safe_parse_datetime(departure_time) if departure_time else now_datetime()

    # ✅ Create Delivery Trip
    trip = frappe.new_doc("Delivery Trip")
    trip.driver = driver
    trip.vehicle = vehicle
    trip.employee = employee
    trip.total_distance = total_distance
    trip.departure_time = parsed_departure

    # Add Delivery Stops
    if delivery_stops:
        for stop in delivery_stops:
            trip.append("delivery_stops", {
                "customer": stop.get("customer"),
                "address": stop.get("address"),
                "delivery_note": stop.get("delivery_note"),
                "estimated_arrival": safe_parse_datetime(stop.get("estimated_arrival"))
                    if stop.get("estimated_arrival") else None
            })

    trip.insert(ignore_permissions=True)
    trip.submit()

    # ✅ Create Expense Claim (only if expenses provided)
    expense_claim = None
    if expenses:
        expense_claim = frappe.new_doc("Expense Claim")
        expense_claim.employee = employee
        expense_claim.expense_date = today()
        expense_claim.company = frappe.defaults.get_global_default("company")
        expense_claim.delivery_trip = trip.name
        expense_claim.expense_approver = "martin@gmail.com"

        for exp in expenses:
            expense_claim.append("expenses", {
                "expense_type": exp.get("expense_type") or "Vehicle Expenses",
                "description": exp.get("description"),
                "amount": exp.get("amount")
            })

        expense_claim.insert(ignore_permissions=True)
        # expense_claim.submit()  # Uncomment if you want auto-submit

    return {
        "delivery_trip": trip.name,
        "expense_claim": expense_claim.name if expense_claim else None
    }

# --- Helper function to safely parse datetime ---
def safe_parse_datetime(dt_str):
    """Try to parse datetime in either DD-MM-YYYY or YYYY-MM-DD formats."""
    if not dt_str:
        return None
    try:
        # First try standard Frappe parsing
        return get_datetime(dt_str)
    except Exception:
        try:
            # Convert from DD-MM-YYYY HH:MM:SS to YYYY-MM-DD HH:MM:SS
            date_part, time_part = dt_str.split(" ")
            d, m, y = date_part.split("-")
            return f"{y}-{m}-{d} {time_part}"
        except Exception:
            frappe.throw(f"Invalid datetime format: {dt_str}")
