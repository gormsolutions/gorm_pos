import frappe

# @frappe.whitelist()
# def set_add_to_transit(stock_entry_name):
#     """
#     Force add_to_transit = 0 for a Stock Entry if:
#       - purpose is 'Material Transfer'
#       - to_warehouse is NOT a transit warehouse

#     Uses update_modified=False to avoid version conflicts.
#     """

#     # Fetch values in one query
#     se_values = frappe.db.get_value(
#         "Stock Entry",
#         stock_entry_name,
#         ["purpose", "to_warehouse", "add_to_transit"],
#         as_dict=True
#     )

#     if not se_values:
#         return f"❌ Stock Entry '{stock_entry_name}' does not exist."

#     transit_warehouses = ["Goods In Transit - DC", "Goods In Transit - CCML"]

#     if se_values.purpose != "Material Transfer":
#         return f"ℹ️ Stock Entry '{stock_entry_name}' is not 'Material Transfer'. Skipped."

#     if se_values.to_warehouse in transit_warehouses:
#         return f"ℹ️ Stock Entry '{stock_entry_name}' is already a transit warehouse. Skipped."

#     if se_values.add_to_transit == 1:
#         frappe.db.set_value(
#             "Stock Entry",
#             stock_entry_name,
#             "add_to_transit",
#             0,
#             update_modified=False  # don’t mess with Modified By / Date
#         )
#         frappe.db.commit()
#         return f"✅ add_to_transit reset to 0 for '{stock_entry_name}'."

#     return f"✔️ add_to_transit already 0 for '{stock_entry_name}'."

@frappe.whitelist()
def set_add_to_transit(stock_entry_name):
    """
    Force add_to_transit = 0 for a Stock Entry if:
      - purpose is 'Material Transfer'
      - to_warehouse is NOT a transit warehouse (based on warehouse_type)

    Uses update_modified=False to avoid version conflicts.
    """

    # Fetch Stock Entry values
    se_values = frappe.db.get_value(
        "Stock Entry",
        stock_entry_name,
        ["purpose", "to_warehouse", "add_to_transit"],
        as_dict=True
    )

    if not se_values:
        return f"❌ Stock Entry '{stock_entry_name}' does not exist."

    if se_values.purpose != "Material Transfer":
        return f"ℹ️ Stock Entry '{stock_entry_name}' is not 'Material Transfer'. Skipped."

    if not se_values.to_warehouse:
        return f"ℹ️ Stock Entry '{stock_entry_name}' has no target warehouse. Skipped."

    # Check warehouse type dynamically
    warehouse_type = frappe.db.get_value("Warehouse", se_values.to_warehouse, "warehouse_type")
    if warehouse_type == "Transit":
        return f"ℹ️ Stock Entry '{stock_entry_name}' targets a transit warehouse. Skipped."

    # Reset add_to_transit if needed
    if se_values.add_to_transit == 1:
        frappe.db.set_value(
            "Stock Entry",
            stock_entry_name,
            "add_to_transit",
            0,
            update_modified=False
        )
        frappe.db.commit()
        return f"✅ add_to_transit reset to 0 for '{stock_entry_name}'."

    return f"✔️ add_to_transit already 0 for '{stock_entry_name}'."
