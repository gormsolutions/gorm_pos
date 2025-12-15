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
    new_account_number,
    company,
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

            # Validate account number
            if not new_account_number or not new_account_number.strip():
                frappe.throw(_("New Account Number cannot be empty."))

            new_account_number = new_account_number.strip()

            # Use new account name if provided, else keep existing
            final_account_name = (
                new_account_name.strip()
                if new_account_name and new_account_name.strip()
                else acc.account_name
            )

            company_abbr = frappe.db.get_value("Company", company, "abbr")

            # Build new document name
            new_doc_name = f"{new_account_number} - {final_account_name} - {company_abbr}"

            # Check duplicate
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
            updated_acc.account_number = new_account_number
            updated_acc.account_name = final_account_name
            updated_acc.save()

            frappe.db.commit()

            return {
                "status": "success",
                "msg": _("Account number and name updated successfully."),
                "new_name": renamed_name,
                "account_number": new_account_number,
                "account_name": final_account_name
            }

        except frappe.QueryTimeoutError:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            frappe.log_error(frappe.get_traceback(), "Account Update Deadlock")
            frappe.throw(_("⛔️ Lock wait timeout. Please try again later."))

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Account Update Error")
            frappe.throw(_("❌ Failed to update account: {0}").format(str(e)))
