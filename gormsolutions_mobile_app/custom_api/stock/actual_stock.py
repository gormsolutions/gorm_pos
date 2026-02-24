import frappe

@frappe.whitelist()
def get_stock_qty(cost_center=None):
    """
    Fetch stock quantities along with the current buying price as the valuation rate,
    and fallback to the valuation rate from the Bin table if no buying price exists.
    Ensure the buying price is fetched only if the stock_uom matches the uom in the Item Price.
    Optionally filter by cost center and restrict to the warehouse 'Main Store Kumi Road - SD'.
    Disabled items are filtered out.
    """
    # Base query
    query = """
        SELECT 
            bin.item_code, 
            bin.actual_qty,
            COALESCE(
                (SELECT price_list_rate
                 FROM `tabItem Price` 
                 WHERE `tabItem Price`.item_code = bin.item_code 
                 AND `tabItem Price`.price_list = 'Standard Buying'
                 AND `tabItem Price`.uom = item.stock_uom
                 ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
                 LIMIT 1),
                bin.valuation_rate
            ) AS valuation_rate,
            (SELECT price_list_rate
             FROM `tabItem Price` 
             WHERE `tabItem Price`.item_code = bin.item_code 
             AND `tabItem Price`.price_list = 'Standard Selling'
             AND `tabItem Price`.uom = item.stock_uom
             ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
             LIMIT 1) AS selling_price,
            item.stock_uom AS uom
        FROM 
            `tabBin` AS bin
        JOIN 
            `tabItem` AS item ON bin.item_code = item.name
        JOIN 
            `tabWarehouse` AS warehouse ON bin.warehouse = warehouse.name
        WHERE 
            warehouse.name = %s
            AND item.disabled = 0
    """

    # Parameters for the query
    params = ["Main Store Kumi Road - SD"]

    # Optional filter for cost_center
    if cost_center:
        query += " AND warehouse.custom_cost_centre = %s"
        params.append(cost_center)

    # Execute the query
    stock_qty = frappe.db.sql(query, params, as_dict=True)
    
    return stock_qty


@frappe.whitelist()
def get_stock_qty_ashlink(cost_center=None):
    """
    Fetch stock quantities directly from Stock Ledger Entries (SLE) along with:
    - Current buying price as valuation rate (fallback to average valuation rate from SLE if no Item Price exists).
    - Selling price from Item Price.
    - UOM from Item.
    - Show stock per specific warehouse, include positive, negative, and zero balances.
    - Only hide items/warehouses that never appeared in Stock Ledger.
    Optionally filter by cost center, but do not restrict to a specific warehouse.
    """

    query = """
        SELECT
            sle.item_code,
            sle.warehouse,
            SUM(sle.actual_qty) AS actual_qty,
            COALESCE(
                (SELECT price_list_rate
                 FROM `tabItem Price`
                 WHERE `tabItem Price`.item_code = sle.item_code
                 AND `tabItem Price`.price_list = 'Standard Buying'
                 AND `tabItem Price`.uom = item.stock_uom
                 ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
                 LIMIT 1),
                AVG(sle.valuation_rate)  -- fallback if no buying price exists
            ) AS valuation_rate,
            (SELECT price_list_rate
             FROM `tabItem Price`
             WHERE `tabItem Price`.item_code = sle.item_code
             AND `tabItem Price`.price_list = 'Standard Selling'
             AND `tabItem Price`.uom = item.stock_uom
             ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
             LIMIT 1) AS selling_price,
            item.stock_uom AS uom
        FROM
            `tabStock Ledger Entry` AS sle
        JOIN
            `tabItem` AS item ON sle.item_code = item.name
        JOIN
            `tabWarehouse` AS warehouse ON sle.warehouse = warehouse.name
        WHERE
            sle.docstatus < 2
    """

    params = []

    # Optional cost center filter
    if cost_center:
        query += " AND warehouse.custom_cost_centre = %s"
        params.append(cost_center)

    query += """
        GROUP BY sle.item_code, sle.warehouse
    """

    stock_qty = frappe.db.sql(query, params, as_dict=True)

    return stock_qty



@frappe.whitelist()
def reset_password_and_update_image(new_password=None, image_url=None):
    try:
        # Get the logged-in user's email
        user_email = frappe.session.user
        
        # Fetch the user document
        user = frappe.get_doc("User", user_email)
        
        # Reset the password if provided
        if new_password:
            frappe.utils.password.update_password(user_email, new_password)
        
        # Update the profile image if provided
        if image_url:
            user.user_image = image_url
            user.save()
        else:
            # Save the user document even if no updates are made
            user.save()

        frappe.db.commit()  # Commit the transaction

        # Dynamic success message
        message = f"User: {user_email} updated successfully."
        if new_password:
            message += " Password reset completed."
        if image_url:
            message += " Profile image updated."

        return {
            "status": "success",
            "message": message
        }
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": f"User with email {user_email} does not exist"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }

import frappe

@frappe.whitelist()
def get_user_doc():
    try:
        # Get the logged-in user's email
        user_email = frappe.session.user

        # Fetch the User document
        user_doc = frappe.get_doc("User", user_email)

        # Convert the document to a dictionary for API response
        user_data = user_doc.as_dict()

        # Return the user document
        return {
            "status": "success",
            "user_data": user_data
        }
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": "User does not exist"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }

# @frappe.whitelist()
# def get_stock_qty_roots(cost_center=None):
#     """
#     Fetch stock quantities along with the current buying price as the valuation rate,
#     and fallback to the valuation rate from the Bin table if no buying price exists.
#     Ensure the buying price is fetched only if the stock_uom matches the uom in the Item Price.
#     Optionally filter by cost center and restrict to the warehouse 'Stores - RL'.
#     Only include items where custom_on_selling_pos = 1.
#     """
#     # Base query
#     query = """
#         SELECT 
#             bin.item_code, 
#             bin.actual_qty,
#             COALESCE(
#                 (SELECT price_list_rate
#                  FROM `tabItem Price` 
#                  WHERE `tabItem Price`.item_code = bin.item_code 
#                  AND `tabItem Price`.price_list = 'Standard Buying'
#                  AND `tabItem Price`.uom = item.stock_uom
#                  ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
#                  LIMIT 1),
#                 bin.valuation_rate
#             ) AS valuation_rate,
#             (SELECT price_list_rate
#              FROM `tabItem Price` 
#              WHERE `tabItem Price`.item_code = bin.item_code 
#              AND `tabItem Price`.price_list = 'Standard Selling'
#              AND `tabItem Price`.uom = item.stock_uom
#              ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
#              LIMIT 1) AS selling_price,
#             item.stock_uom AS uom
#         FROM 
#             `tabBin` AS bin
#         JOIN 
#             `tabItem` AS item ON bin.item_code = item.name
#         JOIN 
#             `tabWarehouse` AS warehouse ON bin.warehouse = warehouse.name
#         WHERE 
#             warehouse.name = %s
#             AND item.custom_on_selling_pos = 1
#     """

#     # Parameters for the query
#     params = ["Stores - RL"]

#     # Add an optional filter for cost_center if provided
#     if cost_center:
#         query += " AND warehouse.custom_cost_centre = %s"
#         params.append(cost_center)

#     # Execute the query
#     stock_qty = frappe.db.sql(query, params, as_dict=True)
    
#     return stock_qty


@frappe.whitelist()
def get_stock_qty_roots(cost_center=None):
    """
    Fetch all items including those with no stock in the warehouse.
    """
    query = """
        SELECT 
            item.name AS item_code,
            COALESCE(bin.actual_qty, 0) AS actual_qty,
            COALESCE(
                (SELECT price_list_rate
                 FROM `tabItem Price` 
                 WHERE `tabItem Price`.item_code = item.name 
                 AND `tabItem Price`.price_list = 'Standard Buying'
                 AND `tabItem Price`.uom = item.stock_uom
                 ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
                 LIMIT 1),
                COALESCE(bin.valuation_rate, 0)
            ) AS valuation_rate,
            (SELECT price_list_rate
             FROM `tabItem Price` 
             WHERE `tabItem Price`.item_code = item.name 
             AND `tabItem Price`.price_list = 'Standard Selling'
             AND `tabItem Price`.uom = item.stock_uom
             ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
             LIMIT 1) AS selling_price,
            item.stock_uom AS uom
        FROM 
            `tabItem` AS item
        LEFT JOIN 
            `tabBin` AS bin 
            ON bin.item_code = item.name
        LEFT JOIN 
            `tabWarehouse` AS warehouse 
            ON bin.warehouse = warehouse.name
        WHERE 
            item.custom_on_selling_pos = 1
    """

    params = []

    # Optional cost center filter
    if cost_center:
        query += " AND (warehouse.custom_cost_centre = %s OR warehouse.custom_cost_centre IS NULL)"
        params.append(cost_center)

    # Optional warehouse filter (only include 'Stores - RL' bins if exists)
    query += " AND (warehouse.name = %s OR warehouse.name IS NULL)"
    params.append("Stores - RL")
    stock_qty = frappe.db.sql(query, params, as_dict=True)
    return stock_qty

@frappe.whitelist()
def get_stock_qty_omacom(cost_center=None):
    """
    Fetch stock quantity and prices for each item in each warehouse.
    Excludes items that have no warehouse (NULL warehouse).
    Omits disabled items.
    """
    query = """
        SELECT 
            item.name AS item_code,
            warehouse.name AS warehouse,
            COALESCE(bin.actual_qty, 0) AS actual_qty,
            COALESCE(
                (SELECT price_list_rate
                 FROM `tabItem Price`
                 WHERE `tabItem Price`.item_code = item.name
                   AND `tabItem Price`.price_list = 'Standard Buying'
                   AND `tabItem Price`.uom = item.stock_uom
                 ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
                 LIMIT 1),
                COALESCE(bin.valuation_rate, 0)
            ) AS valuation_rate,
            (SELECT price_list_rate
             FROM `tabItem Price`
             WHERE `tabItem Price`.item_code = item.name
               AND `tabItem Price`.price_list = 'Standard Selling'
               AND `tabItem Price`.uom = item.stock_uom
             ORDER BY `tabItem Price`.valid_from DESC, `tabItem Price`.creation DESC
             LIMIT 1) AS selling_price,
            item.stock_uom AS uom
        FROM 
            `tabItem` AS item
        LEFT JOIN 
            `tabBin` AS bin ON bin.item_code = item.name
        LEFT JOIN 
            `tabWarehouse` AS warehouse ON bin.warehouse = warehouse.name
        WHERE 
            warehouse.name IS NOT NULL
            AND item.disabled = 0
    """

    params = []

    # Optional cost center filter
    if cost_center:
        query += " AND (warehouse.custom_cost_centre = %s)"
        params.append(cost_center)

    # Order results by item and warehouse
    query += " ORDER BY item.name, warehouse.name"

    stock_qty = frappe.db.sql(query, params, as_dict=True)
    return stock_qty
