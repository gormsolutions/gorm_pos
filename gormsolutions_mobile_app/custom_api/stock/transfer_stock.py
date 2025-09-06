import frappe
from frappe import _

@frappe.whitelist()
def create_material_transfer_ashlink(items, customer=None):     # <-- made optional
    try:
        current_user = frappe.session.user

        # Fetch default warehouse from User Permissions (Source Warehouse)
        user_permissions = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Warehouse", "is_default": 1},
            fields=["for_value"]
        )

        default_warehouses = [perm["for_value"] for perm in user_permissions]
        source_warehouse = default_warehouses[0] if default_warehouses else None

        if not source_warehouse:
            frappe.throw(_("Source warehouse not found. Please set it in User Permissions."))

        import json
        items_payload = json.loads(items) if isinstance(items, str) else (items or [])
        if not items_payload:
            frappe.throw(_("No items provided for Material Transfer."))

        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Transfer"
        if customer:                       # <-- only set if provided
            stock_entry.custom_customer = customer
        stock_entry.posting_date = frappe.utils.today()

        for item in items_payload:
            stock_entry.to_warehouse = item.get("warehouse")
            stock_entry.append("items", {
                "item_code": item.get("item_code"),
                "qty": item.get("qty"),
                "uom": item.get("uom"),
                "s_warehouse": source_warehouse,
                "t_warehouse": item.get("warehouse")
            })

        stock_entry.insert()
        stock_entry.submit()

        return {
            "status": "success",
            "message": _("Material Transfer created successfully."),
            "stock_entry": stock_entry.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Material Transfer Creation Error")
        return {
            "status": "error",
            "message": _("Error creating Material Transfer. Please try again."),
            "error_detail": str(e)
        }

import frappe
from frappe import _

@frappe.whitelist()
def get_non_default_user_warehouses():
    """
    Fetch warehouses from User Permissions where is_default == 0
    for the current session user.
    """
    try:
        current_user = frappe.session.user

        warehouses = frappe.get_all(
            "User Permission",
            filters={
                "user": current_user,
                "allow": "Warehouse",
                "is_default": 0
            },
            fields=["for_value"]
        )

        warehouse_list = [w["for_value"] for w in warehouses]

        return {
            # "status": "success",
            "warehouses": warehouse_list
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Fetch Non-Default Warehouses Error")
        return {
            "status": "error",
            "message": _("Could not fetch warehouses."),
            "error_detail": str(e)
        }

# import frappe
# from frappe import _

# @frappe.whitelist()
# def create_material_return_ashlink(items):
#     try:
#         current_user = frappe.session.user

#         # Fetch default warehouse from User Permissions (Source Warehouse)
#         user_permissions = frappe.get_all(
#             "User Permission",
#             filters={"user": current_user, "allow": "Warehouse", "is_default": 1},
#             fields=["for_value"]
#         )

#         default_warehouses = [perm["for_value"] for perm in user_permissions]
#         source_warehouse = default_warehouses[0] if default_warehouses else None

#         if not source_warehouse:
#             frappe.throw(_("Source warehouse not found. Please set it in User Permissions."))

#         # Parse item quantities from JSON string to Python dictionary
#         import json
#         items_payload = json.loads(items) if isinstance(items, str) else (items or [])

#         if not items_payload:
#             frappe.throw(_("No items provided for Material Transfer."))

#         # Create a Stock Entry (Material Transfer)
#         stock_entry = frappe.new_doc("Stock Entry")
#         stock_entry.stock_entry_type = "Material Transfer"
#         stock_entry.posting_date = frappe.utils.today()
#         stock_entry.to_warehouse = source_warehouse
       

#         for item in items_payload: 
#             stock_entry.from_warehouse = item.get("warehouse")
#             stock_entry.append("items", {
#                 "item_code": item.get("item_code"),
#                 "qty": item.get("qty"),
#                 "uom": item.get("uom"),
#                 "s_warehouse": item.get("warehouse"),
#                 "t_warehouse": source_warehouse,
#             })

#         # Insert & submit Stock Entry
#         stock_entry.insert()
#         stock_entry.submit()

#         return {
#             "status": "success",
#             "message": _("Material Transfer created successfully."),
#             "stock_entry": stock_entry.name
#         }

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Material Transfer Creation Error")
#         return {
#             "status": "error",
#             "message": _("Error creating Material Transfer. Please try again."),
#             "error_detail": str(e)
#         }

import frappe
from frappe import _
from erpnext.stock.utils import get_stock_balance
from frappe.utils import get_datetime

@frappe.whitelist()
def create_material_return_ashlink(items):
    try:
        current_user = frappe.session.user

        # Get default target warehouse
        user_permissions = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Warehouse", "is_default": 1},
            fields=["for_value"]
        )
        default_warehouses = [perm["for_value"] for perm in user_permissions]
        target_warehouse = default_warehouses[0] if default_warehouses else None

        if not target_warehouse:
            frappe.throw(_("Target warehouse not found. Please set it in User Permissions."))

        # Parse items payload
        import json
        items_payload = json.loads(items) if isinstance(items, str) else (items or [])
        if not items_payload:
            frappe.throw(_("No items provided for Material Transfer."))

        posting_datetime = get_datetime(frappe.utils.now())

        shortages = []
        for item in items_payload:
            item_code = item.get("item_code")
            from_warehouse = item.get("warehouse")
            qty = float(item.get("qty") or 0)
            uom = item.get("uom") or ""

            # Get stock UOM
            stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
            if not stock_uom:
                frappe.throw(_("Stock UOM not set for item {0}").format(item_code))

            # Calculate conversion factor manually
            if uom != stock_uom:
                conv_factor = frappe.db.get_value(
                    "UOM Conversion Detail",
                    {"parent": item_code, "uom": uom},
                    "conversion_factor"
                )
                if not conv_factor:
                    frappe.throw(_("Conversion factor not found for item {0} from {1} to {2}").format(
                        item_code, uom, stock_uom))
            else:
                conv_factor = 1.0

            qty_in_stock_uom = qty * conv_factor

            # Check actual stock from stock ledger
            actual_qty = get_stock_balance(
                item_code=item_code,
                warehouse=from_warehouse,
                posting_date=posting_datetime.date(),
                posting_time=posting_datetime.time(),
                with_valuation_rate=False
            ) or 0

            if qty_in_stock_uom > actual_qty:
                shortages.append(
                    _("Item {0} in {1}: Requested {2} {3} ({4} in stock UOM), Available {5}").format(
                        item_code, from_warehouse, qty, uom, qty_in_stock_uom, actual_qty
                    )
                )

        if shortages:
            frappe.throw(
                _("Cannot proceed with Material Transfer due to insufficient stock:<br>") +
                "<br>".join(shortages),
                title=_("Insufficient Stock")
            )

        # Create Stock Entry
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Transfer"
        stock_entry.posting_date = posting_datetime.date()
        stock_entry.posting_time = posting_datetime.time()
        stock_entry.to_warehouse = target_warehouse

        for item in items_payload:
            stock_entry.from_warehouse = item.get("warehouse")
            stock_entry.append("items", {
                "item_code": item.get("item_code"),
                "qty": item.get("qty"),
                "uom": item.get("uom"),
                "s_warehouse": item.get("warehouse"),
                "t_warehouse": target_warehouse,
            })

        stock_entry.insert(ignore_permissions=True)
        stock_entry.submit()

        return {
            "status": "success",
            "message": _("Material Transfer created successfully."),
            "stock_entry": stock_entry.name
        }

    except frappe.ValidationError as e:
        return {
            "status": "error",
            "message": str(e),
            "error_detail": str(e)
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Material Transfer Creation Error")
        return {
            "status": "error",
            "message": _("Unexpected error while creating Material Transfer."),
            "error_detail": str(e)
        }



@frappe.whitelist()
def create_material_return_experies(items):
    try:
        current_user = frappe.session.user

        # Fetch default warehouse from User Permissions (Source Warehouse)
        user_permissions = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Warehouse", "is_default": 1},
            fields=["for_value"]
        )

        default_warehouses = [perm["for_value"] for perm in user_permissions]
        source_warehouse = default_warehouses[0] if default_warehouses else None
        
        # Fetch default warehouse from User Permissions (Source Warehouse)
        damaged_store = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Warehouse", "custom_damaged_store": 1},
            fields=["for_value"]
        )

        default_warehouses_damaged = [perm["for_value"] for perm in damaged_store]
        source_warehouse_damaged = default_warehouses_damaged[0] if default_warehouses_damaged else None

        if not source_warehouse:
            frappe.throw(_("Source warehouse not found. Please set it in User Permissions."))
        
        if not source_warehouse_damaged:
            frappe.throw(_("damaged warehouse not found. Please set it in User Permissions."))

        # Parse item quantities from JSON string to Python dictionary
        import json
        items_payload = json.loads(items) if isinstance(items, str) else (items or [])

        if not items_payload:
            frappe.throw(_("No items provided for Material Transfer."))

        # Create a Stock Entry (Material Transfer)
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Transfer"
        stock_entry.posting_date = frappe.utils.today()
        stock_entry.to_warehouse = source_warehouse
       

        for item in items_payload: 
            stock_entry.from_warehouse = item.get("warehouse")
            stock_entry.append("items", {
                "item_code": item.get("item_code"),
                "qty": item.get("qty"),
                "uom": item.get("uom"),
                "s_warehouse":source_warehouse,
                "t_warehouse": source_warehouse_damaged,
            })

        # Insert & submit Stock Entry
        stock_entry.insert()
        stock_entry.submit()

        return {
            "status": "success",
            "message": _("Material Transfer created successfully."),
            "stock_entry": stock_entry.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Material Transfer Creation Error")
        return {
            "status": "error",
            "message": _("Error creating Material Transfer. Please try again."),
            "error_detail": str(e)
        }


# my_app/api/purchase_invoice.py

import frappe
from frappe.utils import nowdate

@frappe.whitelist(allow_guest=False)
def create_purchase_invoice(supplier, items, is_return=False):
    """
    Create and submit a Purchase Invoice (Purchase or Return) via API.
    
    Args:
        supplier: Supplier ID
        is_return: True/False
        items: List of dicts, e.g.:
        [
            {"item_code": "ITEM-0001", "qty": 10, "rate": 100, "uom": "Box"},
            {"item_code": "ITEM-0002", "qty": 5, "rate": 50, "uom": "Pack"}
        ]
    """
    import json
    
    # Parse items if JSON string is passed
    if isinstance(items, str):
        items = json.loads(items)
    is_return = True if str(is_return).lower() in ["true", "1"] else False

    # Fetch warehouse settings
    settings = frappe.get_single("Purchase and Return Settings")
    warehouse = settings.returns_store if is_return else settings.purchase_store

    # Create Purchase Invoice
    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = supplier
    pi.is_return = is_return
    pi.posting_date = nowdate()
    pi.set_warehouse = warehouse
    pi.cost_center = "Main - AEL"

    # Add items
    for i in items:
        item_code = i.get("item_code")
        qty = i.get("qty", 1)
        if is_return:
            qty = -abs(qty)  # Force negative quantity for returns

        # User-specified UOM
        uom = i.get("uom")
        if not uom:
            frappe.throw(f"UOM is required for item {item_code}")

        # Fetch conversion factor from item UOM table
        conversion_factor = 1.0
        item_doc = frappe.get_doc("Item", item_code)
        if hasattr(item_doc, "uoms") and item_doc.uoms:
            matched_uom = [row for row in item_doc.uoms if row.uom == uom]
            if matched_uom:
                conversion_factor = matched_uom[0].conversion_factor
            else:
                frappe.throw(f"UOM '{uom}' not found in Item '{item_code}' UOM table")
        else:
            # If no child table, assume base UOM
            if uom != item_doc.stock_uom:
                frappe.throw(f"Item '{item_code}' does not have UOM '{uom}'")

        pi.append("items", {
            "item_code": item_code,
            "qty": qty,
            "rate": i.get("rate", 0),
            "warehouse": warehouse,
            "uom": uom,
            "conversion_factor": conversion_factor
        })

    # Insert & submit
    pi.insert()
    pi.submit()

    return {
        "message": "Purchase Invoice created successfully",
        "name": pi.name,
        "is_return": pi.is_return,
        "warehouse": warehouse
    }
