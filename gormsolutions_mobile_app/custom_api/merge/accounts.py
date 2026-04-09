# import frappe

# @frappe.whitelist()
# def merge_accounts(old_account, new_account):
#     if old_account == new_account:
#         frappe.throw("Old Account and New Account cannot be the same.")

#     if not frappe.db.exists("Account", old_account):
#         frappe.throw(f"Old account {old_account} does not exist.")

#     if not frappe.db.exists("Account", new_account):
#         frappe.throw(f"New account {new_account} does not exist.")

#     try:
#         # Force merge without rename validation
#         from frappe.model.rename_doc import rename_doc

#         rename_doc(
#             doctype="Account",
#             old=old_account,
#             new=new_account,
#             merge=True,
#             force=True  # <-- BYPASSES rename block
#         )

#         frappe.db.commit()

#         return {
#             "status": "success",
#             "message": f"Successfully merged {old_account} into {new_account}"
#         }

#     except Exception as e:
#         frappe.db.rollback()
#         frappe.throw(f"Error during merge: {str(e)}")


import frappe

@frappe.whitelist()
def merge_accounts(old_account, new_account, batch_size=500):
    """
    Merge all references of old_account into new_account automatically in batches.
    Skips any tables that do not exist.
    """
    if old_account == new_account:
        frappe.throw("Old Account and New Account cannot be the same.")

    if not frappe.db.exists("Account", old_account):
        frappe.throw(f"Old account {old_account} does not exist.")

    if not frappe.db.exists("Account", new_account):
        frappe.throw(f"New account {new_account} does not exist.")

    try:
        # Get all existing tables in the database
        existing_tables = frappe.db.get_tables()

        # Step 1: Find all DocFields that link to Account
        linked_fields = frappe.get_all(
            "DocField",
            filters={"options": "Account", "fieldtype": ["in", ["Link", "Dynamic Link"]]},
            fields=["parent", "fieldname"]
        )

        # Step 2: Update all linked tables in batches
        for link in linked_fields:
            table = link.parent
            field = link.fieldname
            full_table = f"tab{table}"

            # Skip if table doesn't exist
            if full_table not in existing_tables:
                frappe.log_error(message=f"Skipped missing table {full_table}", title="Merge Accounts")
                continue

            total = frappe.db.count(table, filters={field: old_account})
            if total == 0:
                continue

            start = 0
            while start < total:
                frappe.db.sql(f"""
                    UPDATE `{full_table}`
                    SET `{field}`=%s
                    WHERE `{field}`=%s
                    LIMIT {batch_size}
                """, (new_account, old_account))
                frappe.db.commit()
                start += batch_size

        # Step 3: Delete the old account
        frappe.delete_doc("Account", old_account)
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Successfully merged {old_account} into {new_account}"
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.throw(f"Error during merge: {str(e)}")
