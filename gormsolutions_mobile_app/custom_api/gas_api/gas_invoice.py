import frappe
from frappe.model.document import Document
from frappe.exceptions import PermissionError
from datetime import datetime, timedelta

@frappe.whitelist(allow_guest=True)
def create_gas_invoice(customer, items, include_payments=None, mode_of_payment=None):
    try:
        # Get the current user
        current_user = frappe.session.user

        # Get permitted cost centers for the current user
        cost_center_permitted = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Cost Center"},
            fields=["for_value"]
        )

        # Default cost center to use (fetched from permissions)
        default_cost_centers = cost_center_permitted[0]['for_value'] if cost_center_permitted else None

        # Fetch User Permission records for 'Warehouse' allowed for the current user
        fallback_warehouse = frappe.get_all(
            'User Permission',
            filters={'user': current_user, 'allow': 'Warehouse',"is_default":1},
            fields=['for_value']
        )

        # Determine the fallback warehouse value
        fallback_warehouse = fallback_warehouse[0]['for_value'] if fallback_warehouse else None

        # Fetch allowed Price List
        price_list_permissions = frappe.get_all(
            "User Permission",
            filters={"user": current_user, "allow": "Price List"},
            fields=["for_value"]
        )
        price_list = price_list_permissions[0]['for_value'] if price_list_permissions else None

        # Fetch 'Accepted Store Empties' for the current user
        store_warehouse_empties = frappe.get_all(
            'User Permission',
            filters={'user': current_user,"is_default":0,'allow': 'Warehouse'},
            fields=['for_value']
        )
        default_warehouse_empties = store_warehouse_empties[0]['for_value'] if store_warehouse_empties else None

        # Get today's date and time for setting in the document
        today_date = datetime.today().date()  # Get current date
        today_time = datetime.now().strftime("%H:%M:%S")  # Get current time

        # Calculate the due date (10 days from today)
        due_date = today_date + timedelta(days=10)

        # Initialize totals
        total_qty = 0
        grand_totals = 0

        # Creating a new Gas Invoices document
        gas_invoice = frappe.get_doc({
            "doctype": "Gas Invoices",
            "customer": customer,
            "station": default_cost_centers,  # Assign the single value here
            "price_list": price_list,
            "mode_of_payment": mode_of_payment,
            "store_for_empties": default_warehouse_empties,
            "store": fallback_warehouse,
            "date": today_date,
            # "employee": staff,
            "time": today_time,
            "include_payments": include_payments,
            "due_date": due_date
        })

        # Adding items to the child table 'items' and calculating totals
        for item in items:
            qty = item.get("qty", 0)
            
            rate = item.get("rate", 0)
            amount = qty * rate

            # Add item to the child table
            gas_invoice.append("items", {
                "item_code": item.get("item_code"),
                "qty": qty,
                "rate": rate,
                "amount": amount
            })

            # Update total quantity and grand total
            total_qty += qty
            grand_totals += amount

        # Set the totals in the main document
        gas_invoice.total_qty = total_qty
        gas_invoice.grand_totals = grand_totals

        # Insert the Gas Invoices document
        gas_invoice.insert(ignore_permissions=True)
        gas_invoice.submit()

        # Explicit commit to ensure data is saved in the DB
        frappe.db.commit()

        return gas_invoice.name
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Gas Invoice Creation Error")
        return f"Error: {str(e)}"
