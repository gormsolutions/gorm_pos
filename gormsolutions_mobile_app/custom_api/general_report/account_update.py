import time
import frappe
from frappe import _

@frappe.whitelist()
def update_account_number(account, new_account_number, company, max_retries=3):
    for attempt in range(max_retries):
        try:
            acc = frappe.get_doc("Account", account)

            if acc.company != company:
                frappe.throw(_("Account '{0}' does not belong to company '{1}'.").format(acc.name, company))

            if not new_account_number or not new_account_number.strip():
                frappe.throw(_("New Account Number cannot be empty."))

            company_abbr = frappe.db.get_value("Company", company, "abbr")
            new_account_number = new_account_number.strip()
            new_name = f"{new_account_number} - {acc.account_name} - {company_abbr}"

            if frappe.db.exists("Account", new_name):
                frappe.throw(_("An Account with the name '{0}' already exists.").format(new_name))

            new_doc_name = frappe.rename_doc(
                doctype="Account",
                old=acc.name,
                new=new_name,
                force=True
            )

            updated_acc = frappe.get_doc("Account", new_doc_name)
            updated_acc.account_number = new_account_number
            updated_acc.save()
            frappe.db.commit()

            return {
                "status": "success",
                "msg": _("Account renamed and account number updated."),
                "new_name": new_name
            }

        except frappe.QueryTimeoutError:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait and retry
                continue
            else:
                frappe.log_error(frappe.get_traceback(), "Account Update Deadlock")
                frappe.throw(_("⛔️ Lock wait timeout. Please try again later."))

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Account Update Error")
            frappe.throw(_("❌ Failed to update account: {0}").format(str(e)))


import time
import frappe
from frappe import _

@frappe.whitelist()
def update_account_number_and_name(
    account,
    company,
    new_account_number=None,
    new_account_name=None,
    max_retries=3
):
    for attempt in range(max_retries):
        try:
            acc = frappe.get_doc("Account", account)

            # Validate company
            if acc.company != company:
                frappe.throw(
                    _("Account '{0}' does not belong to company '{1}'.")
                    .format(acc.name, company)
                )

            # Decide final account number (OPTIONAL)
            final_account_number = (
                new_account_number.strip()
                if new_account_number and new_account_number.strip()
                else acc.account_number
            )

            # Decide final account name (OPTIONAL)
            final_account_name = (
                new_account_name.strip()
                if new_account_name and new_account_name.strip()
                else acc.account_name
            )

            company_abbr = frappe.db.get_value("Company", company, "abbr")

            # Build new document name safely
            if final_account_number:
                new_doc_name = f"{final_account_number} - {final_account_name} - {company_abbr}"
            else:
                new_doc_name = f"{final_account_name} - {company_abbr}"

            # Prevent duplicates
            if frappe.db.exists("Account", new_doc_name):
                frappe.throw(
                    _("An Account with the name '{0}' already exists.")
                    .format(new_doc_name)
                )

            # Rename document
            renamed_name = frappe.rename_doc(
                doctype="Account",
                old=acc.name,
                new=new_doc_name,
                force=True
            )

            # Update fields
            updated_acc = frappe.get_doc("Account", renamed_name)
            updated_acc.account_number = final_account_number
            updated_acc.account_name = final_account_name
            updated_acc.save()

            frappe.db.commit()

            return {
                "status": "success",
                "msg": _("Account updated successfully."),
                "new_name": renamed_name,
                "account_number": final_account_number,
                "account_name": final_account_name
            }

        except frappe.QueryTimeoutError:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue

            frappe.log_error(
                frappe.get_traceback(),
                "Account Update Deadlock"
            )
            frappe.throw(_("⛔️ Lock wait timeout. Please try again later."))

        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                "Account Update Error"
            )
            frappe.throw(_("❌ Failed to update account: {0}").format(str(e)))

import frappe
from frappe import _
import time

@frappe.whitelist()
def update_account_name(account, new_account_name, company, max_retries=3):
    for attempt in range(max_retries):
        try:
            if not frappe.db.exists("Account", account):
                frappe.throw(_("Account no longer exists. Please reload."))

            acc = frappe.get_doc("Account", account)

            if acc.company != company:
                frappe.throw(_("Account does not belong to selected company."))

            if not new_account_name or not new_account_name.strip():
                frappe.throw(_("New Account Name cannot be empty."))

            company_abbr = frappe.db.get_value("Company", company, "abbr")
            account_number = (acc.account_number or "").strip()
            new_account_name = new_account_name.strip()

            # Build new Account.name
            new_name = (
                f"{account_number} - {new_account_name} - {company_abbr}"
                if account_number
                else f"{new_account_name} - {company_abbr}"
            )

            if frappe.db.exists("Account", new_name):
                frappe.throw(_("Account with this name already exists."))

            # 🔥 Rename ONCE
            new_doc_name = frappe.rename_doc(
                "Account",
                acc.name,
                new_name,
                force=True
            )

            # 🔥 Update fields without reusing old name
            frappe.db.set_value(
                "Account",
                new_doc_name,
                {
                    "account_name": new_account_name,
                    "account_number": account_number
                }
            )

            frappe.db.commit()

            return {
                "status": "success",
                "new_name": new_doc_name
            }

        except frappe.QueryTimeoutError:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            frappe.throw(_("⛔ Lock timeout. Try again."))

        except frappe.DoesNotExistError:
            frappe.throw(_("Account was renamed. Please reload."))

        except Exception:
            frappe.log_error(frappe.get_traceback(), "Account Name Rename Error")
            frappe.throw(_("❌ Failed to update account name"))

