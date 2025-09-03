import frappe

@frappe.whitelist()
def get_all_delivery_trips(from_date=None, to_date=None):
    """
    Fetch all Delivery Trips with driver, vehicle, employee, departure time, and delivery stops.
    Optionally filter by date range.
    """

    filters = {}
    if from_date and to_date:
        filters["departure_time"] = ["between", [from_date, to_date]]

    trips = frappe.get_all("Delivery Trip", filters=filters, pluck="name")

    results = []

    for trip in trips:
        doc = frappe.get_doc("Delivery Trip", trip)
        trip_data = {
            "name": doc.name,
            "driver": doc.driver,
            "driver_name": doc.driver_name,
            "driver_address": doc.driver_address,
            "total_distance": doc.total_distance,
            "vehicle": doc.vehicle,
            "departure_time": doc.departure_time,
            "employee": doc.employee,
            "delivery_stops": []
        }

        for stop in doc.get("delivery_stops", []):
            trip_data["delivery_stops"].append({
                "idx": stop.idx,
                "customer": stop.customer,
                "address_name": stop.address,
                "locked": stop.locked,
                "delivery_note": stop.delivery_note,
                "estimated_arrival": stop.estimated_arrival
            })

        results.append(trip_data)

    return results
