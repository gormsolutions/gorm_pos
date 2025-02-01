import frappe
from frappe import _

@frappe.whitelist()
def create_item(item_data):
    """
    Custom method to create an Item in ERPNext via API
    """
    try:
        # Parse the incoming item data
        item_data = frappe.parse_json(item_data)
        
        if not item_data:
            frappe.throw(_("Item data is missing"))
        
        # Create the Item document
        item_doc = frappe.get_doc({
            "doctype": "Item",
            **item_data
        })
        item_doc.insert()
        frappe.db.commit()

        # After creating the item, send a real-time update
        frappe.publish_realtime(
            event='item_data_update',  # Event name
            message={'items': [item_doc.as_dict()]},  # Send newly created item in real-time
            user=frappe.session.user  # You can limit to specific users if needed
        )

        # Return the success response
        return {
            "status": "success",
            "message": "Item created successfully",
            "item_code": item_doc.item_code
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Item Creation Failed")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def fetch_items():
    """
    Fetch items from the Item DocType and send to WebSocket clients in real-time
    """
    try:
        # Fetch items from the Item DocType with a filter for item group 'Oils'
        items = frappe.get_all('Item', fields=['item_code', 'item_name', 'item_group', 'stock_uom'], filters={'item_group': 'Oils'})
        
        # Publish the event to real-time WebSocket listeners
        frappe.publish_realtime(
            event='item_data_update',  # Event name
            message={'items': items},  # Send item data
            user=frappe.session.user  # You can limit to specific users if needed
        )
        
        return {
            "status": "success",
            "message": "Items fetched successfully",
            "data": items  # Include the fetched items in the response
        }
    except Exception as e:
        # Publish error message to WebSocket listeners
        frappe.publish_realtime(
            event='item_data_error',
            message={'error': str(e)},
            user=frappe.session.user
        )
        return {
            "status": "error",
            "message": str(e)
        }
