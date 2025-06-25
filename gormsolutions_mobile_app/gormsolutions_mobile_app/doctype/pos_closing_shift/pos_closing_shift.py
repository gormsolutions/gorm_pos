# Copyright (c) 2025, mututa paul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, flt, now_datetime

class POSClosingShift(Document):
    def on_submit(self):
        # Automatically close the linked POS Opening Entry when POS Closing Shift is submitted
        if self.pos_opening_entry:
            try:
                opening_entry = frappe.get_doc("POS Opening Entry", self.pos_opening_entry)
                if opening_entry.docstatus == 1:
                    # Set the status to Closed
                    opening_entry.db_set("status", "Closed")
                    # Update the period_end_date to current timestamp
                    opening_entry.db_set("period_end_date", now_datetime())
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Error Closing POS Opening Entry")


    