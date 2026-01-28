
# -*- coding: utf-8 -*-
# Copyright (c) 2025, GORM Solutions and contributors
# For license information, please see license.txt

from __future__ import unicode_literals        #  <— MUST be first

import frappe

@frappe.whitelist()
def get_total_cash_per_account(company=None, from_date=None, to_date=None):
	"""
	Fetch total cash per account where Account Type = 'Cash'
	excluding Airtel Money - AEL and MTN Mobile Money - AEL accounts,
	and excluding cancelled GL Entries.
	"""

	# Base filters
	conditions = ["gle.docstatus = 1", "IFNULL(gle.is_cancelled, 0) = 0"]
	filters = {}

	if company:
		conditions.append("gle.company = %(company)s")
		filters["company"] = company

	if from_date:
		conditions.append("gle.posting_date >= %(from_date)s")
		filters["from_date"] = from_date

	if to_date:
		conditions.append("gle.posting_date <= %(to_date)s")
		filters["to_date"] = to_date

	# SQL Query 	AND gle.account NOT IN ('Airtel Money - AEL', 'MTN Mobile Money - AEL') acc.account_type = 'Cash'
	query = f"""
		SELECT 
			gle.account AS account,
			acc.account_name AS account_name,
			acc.account_number AS employee_id,
			SUM(gle.debit) - SUM(gle.credit) AS total_balance
		FROM 
			`tabGL Entry` gle
		INNER JOIN 
			`tabAccount` acc ON gle.account = acc.name
		WHERE 
			
			acc.account_type IN ('Cash', 'Bank')
		
			AND {' AND '.join(conditions)}
		GROUP BY 
			gle.account, acc.account_name
		ORDER BY 
			acc.account_name
	"""

	results = frappe.db.sql(query, filters, as_dict=True)
	return results


import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def internal_transfers(
	posting_date,
	paid_to,
	paid_from,
	reference_no=None,
	reference_date=None,
	paid_amount=0
):
	"""
	Create an Internal Transfer Payment Entry.
	'paid_to' is automatically picked from the first default_account in the Mode of Payment child table.
	"""

	if not (posting_date and paid_to and paid_from and paid_amount):
		frappe.throw(_("Missing required fields"))


	# Create Payment Entry9
	payment_entry = frappe.new_doc("Payment Entry")
	payment_entry.payment_type = "Internal Transfer"
	payment_entry.posting_date = posting_date
	payment_entry.cost_center = "Main - AEL"  # can be made dynamic
	payment_entry.paid_from = paid_from  # can be made dynamic
	payment_entry.paid_to = paid_to
	payment_entry.reference_no = reference_no
	payment_entry.reference_date = reference_date
	payment_entry.paid_amount = paid_amount
	payment_entry.received_amount = paid_amount

	# Save and submit
	payment_entry.insert()
	payment_entry.submit()

	frappe.msgprint(_(f"Internal Transfer {payment_entry.name} created successfully"))

	return {
		"payment_entry_name": payment_entry.name,
		"paid_to": paid_to,
		"mode_of_payment": paid_from
	}


import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def create_shortage_journal_entry(date, employee, cash_account, amount, company="ASHLINK ENTERPRISE LTD"):
	"""
	Dynamically create a Journal Entry for employee shortage repayment.

	Args:
		date (str): Posting date (YYYY-MM-DD)
		employee (str): Employee ID (e.g. HR-EMP-00001)
		cash_account (str): Account to debit (e.g. BA Cash Account - AEL)
		amount (float): Amount to transfer
		company (str): Company name (optional)
	"""

	# ✅ Fetch employee name
	employee_doc = frappe.get_value("Employee", employee, ["employee_name"])
	employee_name = employee_doc if employee_doc else employee

	# --- Create Journal Entry document ---
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.posting_date = date
	je.company = company
	je.remark = f"Employee shortage repayment for {employee_name}"

	# --- Add Debit line (Cash Account) ---
	je.append("accounts", {
		"account": cash_account,
		"debit_in_account_currency": 0.00,
		"credit_in_account_currency": amount

	   })

	# --- Add Credit line (Employee Shortage Account) ---
	je.append("accounts", {
		"account": "Employee Shortage Account - AEL",
		"party_type": "Employee",
		"party": employee,
		"debit_in_account_currency": amount,
		"credit_in_account_currency": 0.00
	 
	})

	# --- Save and Submit ---
	je.insert(ignore_permissions=True)
	je.submit()

	return {
		"name": je.name,
		"posting_date": je.posting_date,
		"employee": employee,
		"employee_name": employee_name,
		"total_debit": je.total_debit,
		"total_credit": je.total_credit
	}

import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def clear_shortage_journal_entry(date, employee, amount, company="ASHLINK ENTERPRISE LTD"):
	"""
	Dynamically create a Journal Entry for employee shortage repayment.

	Args:
		date (str): Posting date (YYYY-MM-DD)
		employee (str): Employee ID (e.g. HR-EMP-00001)
		cash_account (str): Account to debit (e.g. BA Cash Account - AEL)
		amount (float): Amount to transfer
		company (str): Company name (optional)
	"""

	# ✅ Fetch employee name
	employee_doc = frappe.get_value("Employee", employee, ["employee_name"])
	employee_name = employee_doc if employee_doc else employee

	# --- Create Journal Entry document ---
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.posting_date = date
	je.company = company
	je.remark = f"Employee shortage repayment for {employee_name}"

	# --- Add Debit line (Cash Account) ---
	je.append("accounts", {
		"account": "1110 - Cash - AEL",
		"debit_in_account_currency": amount,
		"credit_in_account_currency": 0.00
	
	

	   })

	# --- Add Credit line (Employee Shortage Account) ---
	je.append("accounts", {
		"account": "Employee Shortage Account - AEL",
		"party_type": "Employee",
		"party": employee,
		"debit_in_account_currency": 0.00,
		"credit_in_account_currency": amount
	
	
	 
	})

	# --- Save and Submit ---
	je.insert(ignore_permissions=True)
	je.submit()

	return {
		"name": je.name,
		"posting_date": je.posting_date,
		"employee": employee,
		"employee_name": employee_name,
		"total_debit": je.total_debit,
		"total_credit": je.total_credit
	}

# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.utils import getdate, flt


@frappe.whitelist()
def fetch_employee_shortages(from_date=None, to_date=None):
    """
    Fetch employees who have a positive balance in the
    'Employee Shortage Account - AEL' ledger.

    Parameters
    ----------
    from_date : str (optional)
        ISO date string (yyyy-mm-dd).  Inclusive.
    to_date   : str (optional)
        ISO date string (yyyy-mm-dd).  Inclusive.

    Returns
    -------
    list[dict]
        Each dict contains:
        - employee        : Employee ID (str)
        - balance         : Outstanding shortage amount (float)
        - employee_name   : Employee’s full name (str)
    """

    # ------------------------------------------------------------------
    # 1. Build dynamic WHERE clause
    # ------------------------------------------------------------------
    conditions = [
        "account = 'Employee Shortage Account - AEL'",
        "IFNULL(is_cancelled,0) = 0",
        "voucher_type = 'Journal Entry'"
    ]
    params = {}

    if from_date:
        conditions.append("posting_date >= %(from_date)s")
        params["from_date"] = getdate(from_date)
    if to_date:
        conditions.append("posting_date <= %(to_date)s")
        params["to_date"] = getdate(to_date)

    where_clause = " AND ".join(conditions)

    # ------------------------------------------------------------------
    # 2. Aggregate shortages from GL Entry
    # ------------------------------------------------------------------
    data = frappe.db.sql(
        f"""
        SELECT
            party            AS employee,
            SUM(debit - credit) AS balance
        FROM `tabGL Entry`
        WHERE {where_clause}
        GROUP BY party
        HAVING balance > 0
        ORDER BY balance DESC
        """,
        params,
        as_dict=1,
    )

    # ------------------------------------------------------------------
    # 3. Enrich with employee names
    # ------------------------------------------------------------------
    for row in data:
        row["employee_name"] = (
            frappe.db.get_value("Employee", row["employee"], "employee_name")
            or row["employee"]
        )

    # ------------------------------------------------------------------
    # 4. Debug logging
    # ------------------------------------------------------------------
    frappe.logger().info(
        "Fetched %s employee shortages (from=%s, to=%s)",
        len(data),
        from_date,
        to_date,
    )

    return data


# -----------------------------
# API 1: Fetch all Employees
# -----------------------------
@frappe.whitelist(allow_guest=True)
def get_employees():
    """
    Returns a list of all employees with key details.
    """
    employees = frappe.get_all(
        "Employee",
        fields=["name", "employee_name", "employee_number", "department", "branch", "status"],
        filters={"status": "Active"}  # optional: only active employees
    )
    
    return {"data": employees}


# -----------------------------
# API 2: Fetch all Locations
# -----------------------------
@frappe.whitelist(allow_guest=True)
def get_locations():
    """
    Returns a list of all locations stored in the system.
    """
    locations = frappe.get_all(
        "Location",  # replace with your doctype for locations if different
        fields=["name"]
    )
    
    return {"data": locations}

import frappe
from frappe import _

@frappe.whitelist()
def fetch_bank_and_cash_accounts():
    """
    Fetch all active leaf accounts (is_group=0, disabled=0) 
    where Account Type is 'Bank' or 'Cash', excluding specific accounts.
    """
    excluded_accounts = [
        "BA Cash Account - AEL",
		"1110 - Cash - AEL",
        "BF Cash Account - AEL",
        "BJ Cash Account - AEL"
    ]

    accounts = frappe.db.get_all(
        'Account',
        filters={
            'account_type': ['in', ['Bank', 'Cash']],
            'is_group': 0,
            'disabled': 0,
            'name': ['not in', excluded_accounts]
        },
        fields=['name', 'account_name', 'account_type', 'account_number'],
        order_by='name'
    )
    return accounts

