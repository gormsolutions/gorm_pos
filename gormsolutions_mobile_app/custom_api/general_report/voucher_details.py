import frappe

@frappe.whitelist()
def get_voucher_details(voucher_type, voucher_no):
    """
    Dynamically fetch details of any voucher by its type and number.
    Includes only important fields from child tables,
    plus Payment Entry reference fields and packed_items details.
    """
    try:
        # Load the document dynamically
        doc = frappe.get_doc(voucher_type, voucher_no)
        meta = frappe.get_meta(voucher_type)

        # --- Basic info ---
        details = {
            "voucher_type": voucher_type,
            "voucher_no": voucher_no,
            "name": doc.name,
            "posting_date": getattr(doc, "posting_date", None),
            "company": getattr(doc, "company", None),
            "customer": getattr(doc, "party", None) or getattr(doc, "customer", None),
            "supplier": getattr(doc, "supplier", None),
            "mode_of_payment": getattr(doc, "mode_of_payment", None),
            "paid_amount": getattr(doc, "paid_amount", None),
            "total": getattr(doc, "grand_total", None) or getattr(doc, "total", None),
            "status": getattr(doc, "status", None),
            "docstatus": doc.docstatus,
            "owner": doc.owner,
            # Payment Entry reference fields
            "reference_no": getattr(doc, "reference_no", None),
            "purpose": getattr(doc, "purpose", None),
            "expense_account": getattr(doc, "expense_account", None),
            "cost_center": getattr(doc, "cost_center", None),
            "reference_date": getattr(doc, "reference_date", None),
        }

        # --- Important field mappings for known child tables ---
        important_fields_map = {
            "items": ["item_code", "item_name", "qty", "rate", "amount", "uom", "income_account"],
            "payments": ["mode_of_payment", "amount", "account"],
            "taxes": ["account_head", "description", "rate", "tax_amount"],
            "accounts": ["account", "party_type", "party", "debit", "credit", "against"],
            "references": [
                "reference_doctype", "reference_name", "total_amount",
                "outstanding_amount", "allocated_amount", "exchange_rate"
            ],
            "packed_items": [
                "item_code", "item_name", "uom", "qty", "packed_qty",
                "warehouse"
            ],
        }

        # --- Detect all child tables dynamically ---
        child_tables = [df.fieldname for df in meta.fields if df.fieldtype == "Table"]

        for table in child_tables:
            child_data = getattr(doc, table, None)
            if child_data:
                details[table] = []

                # Select fields intelligently
                fields_to_include = important_fields_map.get(table)

                # Auto-select fallback if no mapping defined
                if not fields_to_include:
                    table_meta = frappe.get_meta(child_data[0].doctype)
                    fields_to_include = [
                        f.fieldname for f in table_meta.fields
                        if f.fieldtype not in ["Table", "Column Break", "Section Break"]
                    ][:6]

                # Collect key data
                for row in child_data:
                    row_info = {
                        field: getattr(row, field, None)
                        for field in fields_to_include
                    }
                    details[table].append(row_info)

        return details

    except frappe.DoesNotExistError:
        frappe.throw(f"{voucher_type} {voucher_no} not found")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_voucher_details_error")
        frappe.throw(f"Error fetching {voucher_type} details: {str(e)}")
