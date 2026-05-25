import frappe # type: ignore
from frappe.utils import get_datetime, now_datetime # type: ignore
from erpnext.stock.utils import get_stock_balance # type: ignore

@frappe.whitelist()
def get_item_details_buddle(limit, offset, search=None, user=None, last_sync=None):
    current_user = user or frappe.session.user

    # Step 1: Get user's POS Profile
    pos_profiles = frappe.get_all("POS Profile", filters={"disabled": 0}, fields=["name"])
    pos_profile_name = None
    for profile in pos_profiles:
        user_found = frappe.get_all(
            "POS Profile User",
            filters={"parent": profile.name, "user": current_user},
            limit=1
        )
        if user_found:
            pos_profile_name = profile.name
            break

    if not pos_profile_name:
        return []

    pos_profile = frappe.get_doc("POS Profile", pos_profile_name)

    # Step 2: Get permitted item groups
    permitted_item_groups = [row.item_group for row in pos_profile.item_groups if row.item_group]
    if not permitted_item_groups:
        return []

    # Step 2.5: Get selling price list
    selling_price_list = pos_profile.selling_price_list
    if not selling_price_list:
        return []

    # Step 3: Include child item groups
    item_groups_to_filter = permitted_item_groups[:]
    child_groups = frappe.get_all(
        "Item Group",
        filters={"parent_item_group": ["in", permitted_item_groups]},
        fields=["name"]
    )
    item_groups_to_filter.extend([grp["name"] for grp in child_groups])

    # Step 4: Get default warehouse
    default_warehouse = pos_profile.warehouse
    if not default_warehouse:
        frappe.throw("Warehouse is not set in the POS Profile.")

    # Step 5: Build filters
    filters = [["disabled", "=", 0]]

    if search:
        filters.append(["item_name", "like", f"%{search}%"])

    if item_groups_to_filter:
        filters.append(["item_group", "in", item_groups_to_filter])
    else:
        return []

    # Step 6: Add last_sync filter safely
    if last_sync:
        try:
            last_sync_dt = get_datetime(last_sync)
            # Defensive: If last_sync is in future, no data should be returned, so add a filter that yields nothing
            if last_sync_dt > now_datetime():
                # Add impossible filter to return empty list
                filters.append(["modified", "<", "1900-01-01 00:00:00"])
            else:
                filters.append(["modified", ">", last_sync_dt])
        except Exception as e:
            # If parsing fails, log and ignore the last_sync filter to avoid unexpected results
            frappe.log_error(f"Failed to parse last_sync '{last_sync}': {e}")
            # Optionally, you could return [] here to be safe
            # return []

    # Step 7: Fetch items ordered by modified desc
    item_details = frappe.get_all(
        "Item",
        filters=filters,
        fields=[
            "item_code", "item_name", "description", "item_group",
            "image", "is_stock_item", "stock_uom", "modified"
        ],
        start=offset,
        page_length=limit,
        order_by="modified desc"
    )

    # Step 8: Enrich item data
    for item in item_details:
        item_code = item["item_code"]

        # Stock balance
        item["stock"] = get_stock_balance(item_code, default_warehouse) or 0

        # UOM and Prices
        uom_details = [{
            "uom": item["stock_uom"],
            "conversion_factor": 1,
            "price": 0.00
        }]

        conversion_details = frappe.get_all(
            "UOM Conversion Detail",
            filters={"parent": item_code},
            fields=["uom", "conversion_factor"]
        )

        for conv in conversion_details:
            if conv["uom"] != item["stock_uom"]:
                price = frappe.get_value(
                    "Item Price",
                    {
                        "item_code": item_code,
                        "selling": 1,
                        "uom": conv["uom"],
                        "price_list": selling_price_list
                    },
                    "price_list_rate"
                ) or 0.00
                uom_details.append({
                    "uom": conv["uom"],
                    "conversion_factor": conv.get("conversion_factor", 1),
                    "price": price
                })

        # Add stock_uom price
        stock_uom_price = frappe.get_value(
            "Item Price",
            {
                "item_code": item_code,
                "selling": 1,
                "uom": item["stock_uom"],
                "price_list": selling_price_list
            },
            "price_list_rate"
        ) or 0.00
        uom_details[0]["price"] = stock_uom_price

        item["price"] = stock_uom_price
        item["uom_details"] = uom_details

        # Barcodes
        barcodes = frappe.get_all(
            "Item Barcode",
            fields=["barcode", "uom"],
            filters={"parent": item_code}
        )
        item["barcodes"] = [{"barcode": b["barcode"], "uom": b["uom"]} for b in barcodes]

        # Other warehouse stock
        if frappe.has_permission("Bin", "read", throw=False):
            warehouse_stock = frappe.get_all(
                "Bin",
                filters=[
                    ["item_code", "=", item_code],
                    ["warehouse", "!=", default_warehouse],
                ],
                fields=["warehouse", "actual_qty"]
            )
            item["other_warehouse_stock"] = [
                {"warehouse_name": stock["warehouse"], "stock": stock["actual_qty"]}
                for stock in warehouse_stock
            ]

        # Product Bundle
        bundle_name = frappe.db.get_value("Product Bundle", {"new_item_code": item_code})
        if bundle_name:
            bundle_items_raw = frappe.get_all(
                "Product Bundle Item",
                filters={"parent": bundle_name},
                fields=["item_code", "qty", "description"]
            )
            bundle_items = []
            for b in bundle_items_raw:
                component_code = b["item_code"]
                component_stock = get_stock_balance(component_code, default_warehouse) or 0.00
                component_price = frappe.get_value(
                    "Item Price",
                    {
                        "item_code": component_code,
                        "price_list": selling_price_list,
                        "selling": 1
                    },
                    "price_list_rate"
                ) or 0.00
                is_stock_item = frappe.get_value("Item", component_code, "is_stock_item") or 0

                bundle_items.append({
                    "item_code": component_code,
                    "stock": component_stock,
                    "qty": b.get("qty") or 0,
                    "description": b.get("description") or "",
                    "price": component_price,
                    "is_stock_item": is_stock_item
                })

            item["is_bundle"] = True
            item["bundle_items"] = bundle_items
        else:
            item["is_bundle"] = False

    return item_details

@frappe.whitelist(allow_guest=True)
def get_item_count():
    return frappe.db.count("Item", filters={"disabled": 0})


import frappe  # type: ignore
from frappe.utils import get_datetime, now_datetime  # type: ignore
from erpnext.stock.utils import get_stock_balance  # type: ignore

@frappe.whitelist()
def get_item_details_last_sync(limit, offset, search=None, user=None, last_sync=None):
    current_user = user or frappe.session.user

    # ---------- 1. POS Profile ----------
    pos_profiles = frappe.get_all("POS Profile", filters={"disabled": 0}, fields=["name"])
    pos_profile_name = None
    for profile in pos_profiles:
        if frappe.db.exists("POS Profile User", {"parent": profile.name, "user": current_user,"default": 1}):
            pos_profile_name = profile.name
            break
    if not pos_profile_name:
        return []

    pos_profile = frappe.get_doc("POS Profile", pos_profile_name)

    # ---------- 2. Item Groups ----------
    permitted_item_groups = [row.item_group for row in pos_profile.item_groups if row.item_group]
    if not permitted_item_groups:
        return []

    # child groups
    child_groups = frappe.get_all(
        "Item Group",
        filters={"parent_item_group": ["in", permitted_item_groups]},
        pluck="name",
    )
    item_groups_to_filter = permitted_item_groups + child_groups

    # ---------- 3. Selling Price List & Warehouse ----------
    selling_price_list = pos_profile.selling_price_list
    if not selling_price_list:
        return []

    default_warehouse = pos_profile.warehouse
    if not default_warehouse:
        frappe.throw("Warehouse is not set in the POS Profile.")

    # ---------- 4. Base filters ----------
    filters = [["disabled", "=", 0]]
    if search:
        filters.append(["item_name", "like", f"%{search}%"])
    filters.append(["item_group", "in", item_groups_to_filter])

    # ---------- 5. last_sync (creation OR modified) ----------
    or_filters = []
    if last_sync:
        try:
            last_sync_dt = get_datetime(last_sync)
            if last_sync_dt is None or last_sync_dt > now_datetime():
                # future → nothing
                return []

            or_filters = [
                ["creation", ">", last_sync_dt],
                ["modified", ">", last_sync_dt],
            ]
        except Exception as e:
            frappe.log_error(
                title="get_item_details_buddle: bad last_sync",
                message=f"Value: {last_sync!r} | Error: {e}",
            )
            return []   # fail-closed

    # ---------- 6. Fetch items ----------
    item_details = frappe.get_all(
        "Item",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "item_code", "item_name", "description", "item_group",
            "image", "is_stock_item", "stock_uom", "modified", "creation"
        ],
        start=offset,
        page_length=limit,
        order_by="modified desc",
    )

    # ---------- 7. Enrich ----------
    for item in item_details:
        item_code = item["item_code"]

        # stock
        item["stock"] = get_stock_balance(item_code, default_warehouse) or 0

        # UOM & prices
        uom_details = [{
            "uom": item["stock_uom"],
            "conversion_factor": 1,
            "price": 0.00,
        }]
        for conv in frappe.get_all(
            "UOM Conversion Detail",
            filters={"parent": item_code},
            fields=["uom", "conversion_factor"],
        ):
            if conv["uom"] != item["stock_uom"]:
                price = frappe.db.get_value(
                    "Item Price",
                    {
                        "item_code": item_code,
                        "selling": 1,
                        "uom": conv["uom"],
                        "price_list": selling_price_list,
                    },
                    "price_list_rate",
                ) or 0.00
                uom_details.append({
                    "uom": conv["uom"],
                    "conversion_factor": conv.get("conversion_factor", 1),
                    "price": price,
                })

        stock_uom_price = frappe.db.get_value(
            "Item Price",
            {
                "item_code": item_code,
                "selling": 1,
                "uom": item["stock_uom"],
                "price_list": selling_price_list,
            },
            "price_list_rate",
        ) or 0.00
        uom_details[0]["price"] = stock_uom_price
        item["price"] = stock_uom_price
        item["uom_details"] = uom_details

        # barcodes
        item["barcodes"] = [
            {"barcode": b["barcode"], "uom": b["uom"]}
            for b in frappe.get_all(
                "Item Barcode",
                fields=["barcode", "uom"],
                filters={"parent": item_code},
            )
        ]

        # other warehouses
        if frappe.has_permission("Bin", "read", throw=False):
            item["other_warehouse_stock"] = [
                {"warehouse_name": b["warehouse"], "stock": b["actual_qty"]}
                for b in frappe.get_all(
                    "Bin",
                    filters=[
                        ["item_code", "=", item_code],
                        ["warehouse", "!=", default_warehouse],
                    ],
                    fields=["warehouse", "actual_qty"],
                )
            ]

        # product bundle
        bundle_name = frappe.db.get_value("Product Bundle", {"new_item_code": item_code})
        if bundle_name:
            item["is_bundle"] = True
            item["bundle_items"] = [
                {
                    "item_code": b["item_code"],
                    "bundle_qty": b.get("qty") or 0,
                    "description": b.get("description") or "",
                    "stock": get_stock_balance(b["item_code"], default_warehouse) or 0.00,
                    "price": (
                        frappe.db.get_value(
                            "Item Price",
                            {
                                "item_code": b["item_code"],
                                "price_list": selling_price_list,
                                "selling": 1,
                            },
                            "price_list_rate",
                        )
                        or 0.00
                    ),
                    "is_stock_item": frappe.db.get_value("Item", b["item_code"], "is_stock_item") or 0,
                }
                for b in frappe.get_all(
                    "Product Bundle Item",
                    filters={"parent": bundle_name},
                    fields=["item_code", "qty", "description"],
                )
            ]
        else:
            item["is_bundle"] = False

    return item_details


from frappe.utils import get_datetime, now_datetime
import frappe

@frappe.whitelist()
def get_item_details_company(limit, offset, search=None, user=None, last_sync=None):
    current_user = user or frappe.session.user

    # Step 1: Get user's POS Profile
    pos_profile_name = frappe.db.sql("""
        SELECT p.name
        FROM `tabPOS Profile` p
        INNER JOIN `tabPOS Profile User` u ON u.parent = p.name
        WHERE p.disabled = 0 AND u.user = %s
        LIMIT 1
    """, current_user, as_dict=True)
    
    if not pos_profile_name:
        return []

    pos_profile_name = pos_profile_name[0].name

    # Step 2: Get company, warehouse, price list
    pos_data = frappe.db.sql("""
        SELECT company, warehouse, selling_price_list
        FROM `tabPOS Profile`
        WHERE name = %s
    """, pos_profile_name, as_dict=True)[0]

    company = pos_data.company
    warehouse = pos_data.warehouse
    price_list = pos_data.selling_price_list

    if not warehouse or not price_list:
        frappe.throw("Warehouse or Price List is not set in POS Profile")

    # Step 3: Get permitted item groups
    permitted_item_groups = frappe.db.sql("""
        SELECT item_group FROM `tabPOS Item Group`
        WHERE parent = %s
    """, pos_profile_name)
    permitted_item_groups = [row[0] for row in permitted_item_groups]

    if not permitted_item_groups:
        return []

    # Step 4: Get child item groups
    child_groups = frappe.db.sql("""
        SELECT name FROM `tabItem Group`
        WHERE parent_item_group IN %s
    """, (permitted_item_groups,), as_dict=True)
    child_group_names = [d.name for d in child_groups]
    all_item_groups = permitted_item_groups + child_group_names

    # Step 5: Build base SQL query for items
    base_query = """
        SELECT item_code, item_name, description, item_group, image,
               is_stock_item, stock_uom, modified
        FROM `tabItem`
        WHERE disabled = 0 AND custom_company = %s
    """
    conditions = []
    values = [company]

    if search:
        conditions.append("item_name LIKE %s")
        values.append(f"%{search}%")

    if all_item_groups:
        conditions.append("item_group IN %s")
        values.append(tuple(all_item_groups))
    
    if last_sync:
        try:
            last_sync_dt = get_datetime(last_sync)
            if last_sync_dt > now_datetime():
                conditions.append("modified < %s")
                values.append("1900-01-01 00:00:00")
            else:
                conditions.append("modified > %s")
                values.append(last_sync_dt)
        except Exception as e:
            frappe.log_error(f"Invalid last_sync '{last_sync}': {e}")
            # optionally return []

    if conditions:
        base_query += " AND " + " AND ".join(conditions)

    base_query += " ORDER BY modified DESC LIMIT %s OFFSET %s"
    values.extend([int(limit), int(offset)])

    items = frappe.db.sql(base_query, tuple(values), as_dict=True)

    # Step 6: Enrich each item
    for item in items:
        item_code = item.item_code

        # Stock in default warehouse
        stock = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty") or 0
        item["stock"] = stock

        # UOMs
        uom_details = [{
            "uom": item["stock_uom"],
            "conversion_factor": 1,
            "price": 0.00
        }]
        uom_data = frappe.db.sql("""
            SELECT uom, conversion_factor FROM `tabUOM Conversion Detail`
            WHERE parent = %s
        """, item_code, as_dict=True)

        for u in uom_data:
            if u.uom != item["stock_uom"]:
                price = frappe.db.get_value("Item Price", {
                    "item_code": item_code,
                    "price_list": price_list,
                    "selling": 1,
                    "uom": u.uom
                }, "price_list_rate") or 0.00
                uom_details.append({
                    "uom": u.uom,
                    "conversion_factor": u.conversion_factor,
                    "price": price
                })

        # Price for stock UOM
        stock_price = frappe.db.get_value("Item Price", {
            "item_code": item_code,
            "price_list": price_list,
            "selling": 1,
            "uom": item["stock_uom"]
        }, "price_list_rate") or 0.00
        uom_details[0]["price"] = stock_price
        item["price"] = stock_price
        item["uom_details"] = uom_details

        # Barcodes
        barcodes = frappe.db.sql("""
            SELECT barcode, uom FROM `tabItem Barcode`
            WHERE parent = %s
        """, item_code, as_dict=True)
        item["barcodes"] = barcodes

        # Other warehouse stock (if permission allows)
        if frappe.has_permission("Bin", "read", throw=False):
            other_stocks = frappe.db.sql("""
                SELECT warehouse, actual_qty FROM `tabBin`
                WHERE item_code = %s AND warehouse != %s
            """, (item_code, warehouse), as_dict=True)
            item["other_warehouse_stock"] = [
                {"warehouse_name": d.warehouse, "stock": d.actual_qty}
                for d in other_stocks
            ]

        # Product Bundle check
        bundle_name = frappe.db.get_value("Product Bundle", {"new_item_code": item_code}, "name")
        if bundle_name:
            bundle_items = frappe.db.sql("""
                SELECT item_code FROM `tabProduct Bundle Item`
                WHERE parent = %s
            """, bundle_name, as_dict=True)
            enriched_bundle_items = []
            for b in bundle_items:
                component_code = b.item_code
                component_stock = frappe.db.get_value("Bin", {
                    "item_code": component_code,
                    "warehouse": warehouse
                }, "actual_qty") or 0
                component_price = frappe.db.get_value("Item Price", {
                    "item_code": component_code,
                    "price_list": price_list,
                    "selling": 1
                }, "price_list_rate") or 0.00
                is_stock_item = frappe.db.get_value("Item", component_code, "is_stock_item") or 0
                enriched_bundle_items.append({
                    "item_code": component_code,
                    "stock": component_stock,
                    "price": component_price,
                    "is_stock_item": is_stock_item
                })

            item["is_bundle"] = True
            item["bundle_items"] = enriched_bundle_items
        else:
            item["is_bundle"] = False

    return items

import frappe  # type: ignore

@frappe.whitelist()
def get_permitted_item_groups(user=None):
    current_user = user or frappe.session.user

    # Step 1: Get user's POS Profile
    pos_profiles = frappe.get_all("POS Profile", filters={"disabled": 0}, fields=["name"])
    pos_profile_name = None
    for profile in pos_profiles:
        user_found = frappe.get_all(
            "POS Profile User",
            filters={"parent": profile.name, "user": current_user},
            limit=1
        )
        if user_found:
            pos_profile_name = profile.name
            break

    if not pos_profile_name:
        return []

    pos_profile = frappe.get_doc("POS Profile", pos_profile_name)

    # Step 2: Return only the permitted item groups (no children)
    permitted_item_groups = [row.item_group for row in pos_profile.item_groups if row.item_group]

    return permitted_item_groups


# In apps/gormsolutions_mobile_app/gormsolutions_mobile_app/custom_api/item.py
import frappe

def disable_negative_stock(doc, method):
    """
    This runs when an Item is saved
    """
    if doc.allow_negative_stock:
        frappe.throw("Allow Negative Stock is not permitted!")
    
    # Optional: Log for debugging
    frappe.log_error(f"Item {doc.name} validation passed", "Negative Stock Check")