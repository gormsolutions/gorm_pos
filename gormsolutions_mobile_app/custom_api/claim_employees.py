import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_employees_and_claim_types():
    # Fetch employees from the Employee doctype
    employees = frappe.get_all("Employee", fields=["name", "employee_name", "department"])
    
    if not employees:
        frappe.throw(_("No employees found"))
    
    # Fetch expense claim types from the Expense Claim Account doctype
    claim_types = frappe.get_all("Expense Claim Type", fields=["name"])
    
    if not claim_types:
        frappe.throw(_("No expense claim types found"))
    
    return {
        "employees": employees,
        "expense_claim_types": claim_types
    }

import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_employees_claim_types_and_cost_centers():
    # Fetch employees from the Employee doctype
    employees = frappe.get_all("Employee", fields=["name", "employee_name", "department"])
    
    if not employees:
        frappe.throw(_("No employees found"))
    
    # Fetch expense claim types from the Expense Claim Account doctype
    claim_types = frappe.get_all("Expense Claim Type", fields=["name"])
    
    if not claim_types:
        frappe.throw(_("No expense claim types found"))
    
    # Fetch cost centers where Is Group = 0
    cost_centers = frappe.get_all("Cost Center", filters={"is_group": 0}, fields=["name", "company"])
    
    if not cost_centers:
        frappe.throw(_("No cost centers found where Is Group = 0"))
    
    return {
        "employees": employees,
        "expense_claim_types": claim_types,
        "cost_centers": cost_centers
    }
