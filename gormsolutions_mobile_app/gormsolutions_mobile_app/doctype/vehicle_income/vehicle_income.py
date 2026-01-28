# Copyright (c) 2026, mututa paul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today
from frappe import _


class VehicleIncome(Document):

	def validate(self):
		# Calculate item amounts and total
		self._calculate_items()
		self._calculate_totals()
		# No need to validate income_account anymore

	def _calculate_items(self):
		for row in self.items or []:
			row.qty = flt(row.qty) or 1
			row.rate = flt(row.rate)
			row.amount = flt(row.qty) * flt(row.rate)

	def _calculate_totals(self):
		self.total_amount = sum(flt(row.amount) for row in self.items or [])

	# -----------------------------
	# on_submit hook: AUTO run
	# -----------------------------
	def on_submit(self):
		# Always create and submit Sales Invoice
		self._create_sales_invoice()

		# Only create Payment Entry if `is_paid` is checked
		if self.is_paid:
			self._create_payment_entry()

	# -----------------------------
	# Internal: Sales Invoice creation
	# -----------------------------
	def _create_sales_invoice(self):
		if self.sales_invoice:
			return  # Already exists

		if not self.customer:
			frappe.throw(_("Customer is required"))

		si = frappe.new_doc("Sales Invoice")
		si.customer = self.customer
		si.company = self.company
		si.posting_date = self.date or today()
		si.due_date = self.date or today()
		si.cost_center = self.cost_center
		si.set_posting_time = 1
		si.update_stock = 0
		si.ignore_pricing_rule = 1

		for row in self.items:
			item_name = row.vehicle or row.get("item_name")
			
			# Fetch default income account for the item
			item_doc = frappe.get_doc("Item", item_name)
			income_account = None
			for d in item_doc.get("item_defaults") or []:
				if d.company == self.company and d.income_account:
					income_account = d.income_account
					break

			if not income_account:
				frappe.throw(_("No Income Account found for Item {0} in company {1}")
							 .format(item_name, self.company))

			si.append("items", {
				"item_name": item_name,
				"qty": flt(row.qty),
				"rate": flt(row.rate),
				"income_account": income_account,
				"cost_center": row.cost_center or self.cost_center
			})

		try:
			si.insert(ignore_permissions=True)
			si.submit()
		except Exception as e:
			frappe.throw(_("Failed to create Sales Invoice: {0}").format(e))

		self.db_set("sales_invoice", si.name)

	# -----------------------------
	# Internal: Payment Entry creation
	# -----------------------------
	def _create_payment_entry(self):
		if not getattr(self, "mode_of_payment", None):
			frappe.throw(_("Mode of Payment is required to post Payment Entry"))

		mop_doc = frappe.get_doc("Mode of Payment", self.mode_of_payment)

		# Get default account for this company
		account = None
		for a in mop_doc.accounts:
			if a.company == self.company:
				account = a.default_account
				break

		if not account:
			frappe.throw(_("No default account found in Mode of Payment for company {0}")
						.format(self.company))

		# Get the Sales Invoice
		si = frappe.get_doc("Sales Invoice", self.sales_invoice)

		# Create Payment Entry
		payment_entry = frappe.new_doc("Payment Entry")
		payment_entry.payment_type = "Receive"
		payment_entry.party_type = "Customer"
		payment_entry.party = self.customer
		payment_entry.company = self.company
		payment_entry.posting_date = self.date or today()
		payment_entry.mode_of_payment = self.mode_of_payment

		# Mandatory fields
		payment_entry.paid_to = account
		payment_entry.paid_to_account_currency = frappe.get_cached_value("Account", account, "account_currency")
		payment_entry.paid_amount = si.outstanding_amount
		payment_entry.received_amount = si.outstanding_amount
		payment_entry.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		payment_entry.target_exchange_rate = 1.0

		# Link to Sales Invoice
		payment_entry.append("references", {
			"reference_doctype": "Sales Invoice",
			"reference_name": si.name,
			"total_amount": si.outstanding_amount,
			"allocated_amount": si.outstanding_amount
		})

		# Insert and submit
		payment_entry.insert(ignore_permissions=True)
		payment_entry.submit()

		# Save in VehicleIncome doc
		self.db_set("payment_entry", payment_entry.name)
