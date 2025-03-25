import frappe
from frappe.model.document import Document
from frappe import _

class PurchaseReturnManagement(Document):
    
    def on_submit(self):
        # Update the supplier_return_status directly in the database
        frappe.db.set_value("Purchase Return Management", self.name, "supplier_return_status", "Items Compensated")
        frappe.db.commit()
        
        # Ensure the reference Purchase Invoice is updated
        self.update_reference_purchase_invoice()
        
        # Create a new Purchase Receipt
        purchase_receipt_name = self.create_purchase_receipt()
        if not purchase_receipt_name:
            frappe.throw("Failed to create Purchase Receipt. Aborting submission.")
        
        # Create the Journal Entry
        journal_entry_name = self.create_journal()
        if not journal_entry_name:
            frappe.throw("Failed to create Journal Entry. Aborting submission.")
    
    def create_purchase_receipt(self):
        try:
            purchase_receipt = frappe.new_doc("Purchase Receipt")
            purchase_receipt.supplier = self.supplier
            purchase_receipt.posting_date = self.posting_date
            purchase_receipt.custom_suplier_return_id = self.name  # Reference to the Purchase Return Management
            purchase_receipt.status = "Completed"
            purchase_receipt.per_billed = 100
            # purchase_receipt.per_returned = 100
            # Add return items to the Purchase Receipt
            for item in self.return_items:
                if item.qty and item.rate:
                    purchase_receipt.append("items", {
                        "item_code": item.item_code,
                        "qty": abs(item.qty),  # Ensure qty is positive
                        "rate": item.rate,
                        "uom": item.uom,
                        "warehouse":item.warehouse
                    })
                else:
                    frappe.throw(f"Invalid item details for {item.item_code}. Ensure quantity and rate are set.")

            # Insert and submit the Purchase Receipt
            purchase_receipt.insert()
            purchase_receipt.submit()
            frappe.db.commit()

            return purchase_receipt.name  # Return the name of the created Purchase Receipt

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Purchase Receipt Creation Error")
            return None

    def update_reference_purchase_invoice(self):
        try:
            if self.reference_purchase_invoice:
                purchase_invoice = frappe.get_doc("Purchase Invoice", self.reference_purchase_invoice)
                purchase_invoice.custom_suplier_return_status = "Items Compensated"
                purchase_invoice.save()
                frappe.db.commit()
            else:
                frappe.throw("Reference Purchase Invoice not found.")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Reference Purchase Invoice Update Error")
            frappe.throw(f"Error updating reference Purchase Invoice: {str(e)}")

    def create_journal(self):
        try:
            existing_receipt = frappe.get_all("Journal Entry", filters={"custom_suplier_return_id": self.name}, limit=1)
            if existing_receipt:
                frappe.msgprint(_(f"Journal Entry already exists for {self.name}"))
                return existing_receipt[0].name

            journal_entry = frappe.new_doc('Journal Entry')
            journal_entry.voucher_type = 'Journal Entry'
            journal_entry.company = 'SANYU DISTRIBUTORS'
            journal_entry.posting_date = self.posting_date
            journal_entry.custom_suplier_return_id = self.name

            # Debit Entry
            journal_entry.append('accounts', {
                'account': "2520 - Stock Received But Not Billed - SD",
                'debit_in_account_currency': self.grand_total,
                'credit_in_account_currency': 0,
            })
                
            # Credit Entry
            journal_entry.append('accounts', {
                'account': "2170 - Creditors - SD",
                'party_type': "Supplier",
                'party': self.supplier,
                'debit_in_account_currency': 0,
                'credit_in_account_currency': self.grand_total,
            })
            
            # Save and submit the Journal Entry
            journal_entry.insert()
            journal_entry.submit()
            frappe.db.commit()
            
            frappe.msgprint(_(f"Successfully created Journal Entry for {self.name}"))
            return journal_entry.name
        
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Journal Entry Creation Error")
            return None
