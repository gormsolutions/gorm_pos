from frappe.model.document import Document
import frappe
import csv
from frappe.utils import get_site_path, nowdate

class GLExport(Document):

    @frappe.whitelist()
    def export_gl(self):
        self.db_set("is_running", 1)
        self.db_set("progress", 0)
        self.db_set("file_url", None)

        frappe.enqueue(
            method="gormsolutions_mobile_app.gormsolutions_mobile_app.doctype.gl_export.gl_export.run_export_gl",
            queue="default",
            timeout=3600,
            job_name=f"GL Export for {self.name}",
            kwargs={"docname": self.name}
        )
        frappe.msgprint("GL Export started in background.")

    def _run_export_gl_now(self):
        filters = {
            "from_date": self.from_date,
            "to_date": self.to_date,
            "company": self.company
        }
        filters = {k: v for k, v in filters.items() if v}

        query = get_gl_query(filters)
        total = get_total_count(query, filters)

        filename = f"gl_entry_export_{nowdate()}.csv"
        file_path = get_site_path("public", "files", filename)

        batch_size = 10000
        offset = 0
        written = 0

        # Get opening balances per account
        opening_balances = get_opening_balances(filters)
        running_balances = opening_balances.copy()

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Posting Date", "Account", "Party Type", "Party", "Cost Center",
                "Debit (NGN)", "Credit (NGN)", "Running Balance (NGN)",
                "Voucher Type", "Voucher No", "Against Voucher",
                "Against Voucher Type", "Project", "Department",
                "Currency", "Remarks", "Company",
                "Voucher Subtype", "Against Account"
            ])

            # Write opening balance rows per account
            for account, opening_balance in opening_balances.items():
                writer.writerow([
                    "",  # No posting date for opening balance row
                    account,
                    "", "", "",
                    0, 0,
                    opening_balance,
                    "Opening Balance", "", "", "", "", "", "", "", "", "", ""
                ])

            while True:
                batch_query = f"{query} LIMIT {batch_size} OFFSET {offset}"
                rows = frappe.db.sql(batch_query, filters, as_dict=True)
                if not rows:
                    break

                for row in rows:
                    account = row.get("account")
                    debit = row.get("debit") or 0
                    credit = row.get("credit") or 0

                    running_balances.setdefault(account, 0)
                    running_balances[account] += (debit - credit)
                    running_balance = running_balances[account]

                    writer.writerow([
                        row.get("posting_date"),
                        account,
                        row.get("party_type"),
                        row.get("party"),
                        row.get("cost_center"),
                        debit,
                        credit,
                        running_balance,
                        row.get("voucher_type"),
                        row.get("voucher_no"),
                        row.get("against_voucher"),
                        row.get("against_voucher_type"),
                        row.get("project"),
                        row.get("department"),
                        row.get("account_currency"),
                        row.get("remarks"),
                        row.get("company"),
                        row.get("voucher_subtype"),
                        row.get("against")
                    ])
                    written += 1

                offset += batch_size
                percent = round((written / total) * 100, 1) if total else 100
                self.db_set("progress", percent)
                frappe.publish_realtime("gl_export_progress", {"progress": percent}, user=self.owner)

        self.db_set("file_url", f"/files/{filename}")
        self.db_set("is_running", 0)
        self.db_set("progress", 100)
        frappe.publish_realtime("gl_export_complete", {"file_url": self.file_url}, user=self.owner)

# Utility functions

def run_export_gl(docname):
    doc = frappe.get_doc("GL Export", docname)
    doc._run_export_gl_now()

def get_conditions(filters):
    # conditions = "docstatus = 1"  # Only submitted entries
    conditions = "docstatus = 1 AND IFNULL(is_cancelled, 0) = 0"
    if filters.get("company"):
        conditions += " AND company = %(company)s"
    if filters.get("from_date"):
        conditions += " AND posting_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND posting_date <= %(to_date)s"
    return conditions

def get_total_count(query, filters):
    count_query = f"SELECT COUNT(*) AS total FROM ({query}) AS total_query"
    result = frappe.db.sql(count_query, filters, as_dict=True)
    return result[0]['total'] if result else 0

def get_gl_query(filters):
    conditions = get_conditions(filters)
    return f"""
        SELECT
            posting_date, account, party_type, party, cost_center,
            debit, credit,
            voucher_type, voucher_no, against_voucher,
            against_voucher_type, project, department,
            account_currency, remarks, company,
            voucher_subtype, against
        FROM `tabGL Entry`
        WHERE {conditions}
        ORDER BY account ASC, posting_date ASC, creation ASC
    """

def get_opening_balances(filters):
    # Calculate opening balances before from_date per account
    if not filters.get("from_date") or not filters.get("company"):
        return {}

    opening_filter = {
        "company": filters["company"],
        "from_date": filters["from_date"]
    }
    query = """
        SELECT account, 
            COALESCE(SUM(debit),0) AS debit, 
            COALESCE(SUM(credit),0) AS credit
        FROM `tabGL Entry`
        WHERE docstatus = 1
          AND company = %(company)s
          AND posting_date < %(from_date)s
        GROUP BY account
    """
    results = frappe.db.sql(query, opening_filter, as_dict=True)
    opening_balances = {}
    for r in results:
        opening_balances[r.account] = (r.debit or 0) - (r.credit or 0)
    return opening_balances

@frappe.whitelist()
def cancel_export_job(docname):
    doc = frappe.get_doc("GL Export", docname)
    job_id = doc.rq_job_id
    if job_id:
        from frappe.utils.background_jobs import get_queue
        q = get_queue("default")
        job = q.fetch_job(job_id)
        if job:
            job.cancel()
            job.delete()
    doc.db_set("is_running", 0)
    doc.db_set("progress", 0)
    doc.db_set("file_url", None)

@frappe.whitelist()
def download_gl_export(docname):
    doc = frappe.get_doc("GL Export", docname)
    filters = {
        "from_date": doc.from_date,
        "to_date": doc.to_date,
        "company": doc.company
    }
    filters = {k: v for k, v in filters.items() if v}
    query = get_gl_query(filters)

    filename = f"gl_entry_export_{nowdate()}.csv"
    file_path = get_site_path("public", "files", filename)

    # Calculate opening balances for download too
    opening_balances = get_opening_balances(filters)
    running_balances = opening_balances.copy()

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Posting Date", "Account", "Party Type", "Party", "Cost Center",
            "Debit (NGN)", "Credit (NGN)", "Running Balance (NGN)",
            "Voucher Type", "Voucher No", "Against Voucher",
            "Against Voucher Type", "Project", "Department",
            "Currency", "Remarks", "Company",
            "Voucher Subtype", "Against Account"
        ])

        # Write opening balances rows
        for account, opening_balance in opening_balances.items():
            writer.writerow([
                "",
                account,
                "", "", "",
                0, 0,
                opening_balance,
                "Opening Balance", "", "", "", "", "", "", "", "", "", ""
            ])

        rows = frappe.db.sql(query, filters, as_dict=True)
        for row in rows:
            account = row.get("account")
            debit = round(row.get("debit") or 0, 2)
            credit = round(row.get("credit") or 0, 2)

            running_balances.setdefault(account, 0)
            running_balances[account] += (debit - credit)
            running_balance = round(running_balances[account], 2) 

            writer.writerow([
                row.get("posting_date"),
                account,
                row.get("party_type"),
                row.get("party"),
                row.get("cost_center"),
                debit,
                credit,
                running_balance,
                row.get("voucher_type"),
                row.get("voucher_no"),
                row.get("against_voucher"),
                row.get("against_voucher_type"),
                row.get("project"),
                row.get("department"),
                row.get("account_currency"),
                row.get("remarks"),
                row.get("company"),
                row.get("voucher_subtype"),
                row.get("against")
            ])

    doc.db_set("file_url", f"/files/{filename}")
    return {
        "file_url": f"/files/{filename}"
    }
