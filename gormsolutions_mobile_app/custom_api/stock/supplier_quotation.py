import frappe

@frappe.whitelist()
def create_supplier_quotation(supplier, items, transaction_date=None, company=None):
    """
    Create a Supplier Quotation in Frappe.
    :param supplier: The supplier for the quotation.
    :param items: A list of dictionaries containing item details (item_code, qty, rate).
    :param transaction_date: The date of the quotation (optional).
    :param company: The company for which the quotation is created (optional).
    :return: A success message or error details.
    """
    try:
        # Create a new Supplier Quotation document
        supplier_quotation = frappe.get_doc({
            "doctype": "Supplier Quotation",
            "supplier": supplier,
            "transaction_date": transaction_date or frappe.utils.nowdate(),
            "company": company or frappe.defaults.get_user_default("Company"),
            "items": [
                {
                    "item_code": item["item_code"],
                    "qty": item["qty"],
                    "rate": item["rate"],
                    "uom": item.get("uom", "Nos")  # Default UOM is 'Nos'
                } for item in items
            ]
        })

        # Insert the document into the database
        supplier_quotation.insert()
        # Submit the document
        supplier_quotation.submit()

        return {
            "status": "success",
            "message": f"Supplier Quotation {supplier_quotation.name} created successfully.",
            "quotation_name": supplier_quotation.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error creating Supplier Quotation")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }