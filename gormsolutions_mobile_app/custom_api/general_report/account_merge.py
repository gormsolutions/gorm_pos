import frappe

BATCH_SIZE = 500  # number of rows to update per batch

@frappe.whitelist()
def custom_merge_accounts_dynamic(source_account, target_account):
    """
    Merge one account into another, updating all links dynamically.
    Uses batching to avoid lock wait timeouts.
    Only use for test/inactive accounts.
    """
    if source_account == target_account:
        frappe.throw("Source and Target accounts cannot be the same")

    # 1️⃣ Get all doctypes that have Link fields pointing to Account
    docfields = frappe.get_all(
        "DocField",
        filters={"options": "Account", "fieldtype": "Link"},
        fields=["parent", "fieldname"]
    )

    # Map: doctype -> list of fields
    doctype_fields = {}
    for df in docfields:
        doctype_fields.setdefault(df.parent, []).append(df.fieldname)

    # 2️⃣ Update all main doctypes in batches
    for dt, fields in doctype_fields.items():
        if not frappe.db.table_exists(f"tab{dt}"):
            continue  # skip missing tables

        for fieldname in fields:
            total_rows = frappe.db.count(dt, filters={fieldname: source_account})
            offset = 0
            while offset < total_rows:
                frappe.db.sql(
                    f"""
                    UPDATE `tab{dt}`
                    SET `{fieldname}` = %s
                    WHERE `{fieldname}` = %s
                    LIMIT {BATCH_SIZE}
                    """,
                    (target_account, source_account)
                )
                frappe.db.commit()
                offset += BATCH_SIZE

    # 3️⃣ Update child tables in batches
    for dt, fields in doctype_fields.items():
        if not frappe.db.table_exists(f"tab{dt}"):
            continue

        meta = frappe.get_meta(dt)
        for df in meta.fields:
            if df.fieldtype == "Table":
                child_doctype = df.options
                if not frappe.db.table_exists(f"tab{child_doctype}"):
                    continue
                child_meta = frappe.get_meta(child_doctype)
                for cdf in child_meta.fields:
                    if cdf.fieldtype == "Link" and cdf.options == "Account":
                        total_rows = frappe.db.count(child_doctype, filters={cdf.fieldname: source_account})
                        offset = 0
                        while offset < total_rows:
                            frappe.db.sql(
                                f"""
                                UPDATE `tab{child_doctype}`
                                SET `{cdf.fieldname}` = %s
                                WHERE `{cdf.fieldname}` = %s
                                LIMIT {BATCH_SIZE}
                                """,
                                (target_account, source_account)
                            )
                            frappe.db.commit()
                            offset += BATCH_SIZE

    # 4️⃣ Delete source account only if no transactions exist
    has_txn = frappe.db.exists("GL Entry", {"account": source_account})
    if not has_txn:
        frappe.delete_doc("Account", source_account, force=True)
        frappe.db.commit()
        return {
            "message": f"Accounts merged successfully: {source_account} → {target_account} (source deleted)"
        }
    else:
        return {
            "message": f"Accounts merged successfully: {source_account} → {target_account} (source retained due to existing transactions)"
        }
