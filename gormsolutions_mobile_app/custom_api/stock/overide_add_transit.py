

import frappe

@frappe.whitelist()
def set_add_to_transit(stock_entry_name):
    """
    Sets add_to_transit = 0 for a Stock Entry if:
    - purpose is 'Material Transfer'
    - to_warehouse is NOT a transit warehouse

    Avoids document conflict by using update_modified=False.
    """
    # Fetch purpose and to_warehouse in one query
    se_values = frappe.db.get_value(
        "Stock Entry",
        stock_entry_name,
        ["purpose", "to_warehouse"],
        as_dict=True
    )

    if not se_values:
        return f"Stock Entry '{stock_entry_name}' does not exist. No changes made."

    purpose = se_values.purpose
    to_warehouse = se_values.to_warehouse

    transit_warehouses = ["Goods In Transit - DC", "Goods In Transit - CCML"]

    if purpose == "Material Transfer":
        if to_warehouse not in transit_warehouses:
            current_value = frappe.db.get_value("Stock Entry", stock_entry_name, "add_to_transit")
            if current_value == 1:
                frappe.db.set_value(
                    "Stock Entry",
                    stock_entry_name,
                    "add_to_transit",
                    0,
                    update_modified=False  # avoid doc modified conflict
                )
                frappe.db.commit()
                # return f"add_to_transit set to 0 for '{stock_entry_name}'."
            # else:
                # return f"add_to_transit is already 0 for '{stock_entry_name}'."
        else:
            return f"Stock Entry '{stock_entry_name}' has a transit warehouse. No changes made."
    else:
        return f"Stock Entry '{stock_entry_name}' purpose is not 'Material Transfer'. No changes made."
