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
            "company": self.company,
            "account": self.account  # ✅ added account to filters
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

            for account, opening_balance in opening_balances.items():
                writer.writerow([
                    "", account, "", "", "", 0, 0, opening_balance,
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


# Utilities

def run_export_gl(docname):
    doc = frappe.get_doc("GL Export", docname)
    doc._run_export_gl_now()

def get_conditions(filters):
    conditions = "docstatus = 1 AND IFNULL(is_cancelled, 0) = 0"
    if filters.get("account"):
        conditions += " AND account = %(account)s"
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
    if not filters.get("from_date") or not filters.get("company"):
        return {}

    query = """
        SELECT account, 
            COALESCE(SUM(debit),0) AS debit, 
            COALESCE(SUM(credit),0) AS credit
        FROM `tabGL Entry`
        WHERE docstatus = 1
          AND company = %(company)s
          AND posting_date < %(from_date)s
        {account_condition}
        GROUP BY account
    """

    # Optional condition for account filter
    account_condition = ""
    if filters.get("account"):
        account_condition = " AND account = %(account)s"
    query = query.format(account_condition=account_condition)

    results = frappe.db.sql(query, filters, as_dict=True)
    return {r.account: (r.debit or 0) - (r.credit or 0) for r in results}

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
        "company": doc.company,
        "account": doc.account  # ✅ include account filter
    }
    filters = {k: v for k, v in filters.items() if v}
    query = get_gl_query(filters)

    filename = f"gl_entry_export_{nowdate()}.csv"
    file_path = get_site_path("public", "files", filename)

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

        for account, opening_balance in opening_balances.items():
            writer.writerow([
                "", account, "", "", "", 0, 0, opening_balance,
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
    return {"file_url": f"/files/{filename}"}

# @frappe.whitelist()
# def fetch_all_gl_entries(
#     from_date=None, to_date=None, company=None, account=None,
#     cost_center=None, party_type=None, party=None, voucher_no=None,
#     limit=1000, offset=0
# ):
#     """
#     Fetch GL entries with advanced filtering, pagination, and additional info.
#     """
#     conditions = ["gle.docstatus = 1", "IFNULL(gle.is_cancelled, 0) = 0"]
#     filters = {}

#     if company:
#         conditions.append("gle.company = %(company)s")
#         filters["company"] = company
#     if account:
#         conditions.append("gle.account = %(account)s")
#         filters["account"] = account
#     if from_date:
#         conditions.append("gle.posting_date >= %(from_date)s")
#         filters["from_date"] = from_date
#     if to_date:
#         conditions.append("gle.posting_date <= %(to_date)s")
#         filters["to_date"] = to_date
#     if cost_center:
#         conditions.append("gle.cost_center = %(cost_center)s")
#         filters["cost_center"] = cost_center
#     if party_type:
#         conditions.append("gle.party_type = %(party_type)s")
#         filters["party_type"] = party_type
#     if party:
#         conditions.append("gle.party = %(party)s")
#         filters["party"] = party
#     if voucher_no:
#         conditions.append("gle.voucher_no = %(voucher_no)s")
#         filters["voucher_no"] = voucher_no

#     where_clause = " AND ".join(conditions)

#     query = f"""
#         SELECT
#             gle.posting_date,
#             gle.account,
#             acc.account_name,
#             gle.party_type,
#             gle.party,
#             IFNULL(cust.customer_name, IFNULL(supp.supplier_name, '')) AS party_name,
#             cc.cost_center_name,
#             gle.debit,
#             gle.credit,
#             gle.voucher_type,
#             gle.voucher_no,
#             gle.against_voucher,
#             gle.against_voucher_type,
#             proj.project_name,
#             dept.department_name,
#             gle.account_currency,
#             gle.remarks,
#             gle.company,
#             gle.voucher_subtype,
#             gle.against
#         FROM `tabGL Entry` gle
#         LEFT JOIN `tabAccount` acc ON acc.name = gle.account
#         LEFT JOIN `tabCustomer` cust ON gle.party_type='Customer' AND gle.party = cust.name
#         LEFT JOIN `tabSupplier` supp ON gle.party_type='Supplier' AND gle.party = supp.name
#         LEFT JOIN `tabCost Center` cc ON cc.name = gle.cost_center
#         LEFT JOIN `tabProject` proj ON proj.name = gle.project
#         LEFT JOIN `tabDepartment` dept ON dept.name = gle.department
#         WHERE {where_clause}
#         ORDER BY gle.account ASC, gle.posting_date ASC, gle.creation ASC
#         LIMIT %(limit)s OFFSET %(offset)s
#     """

#     filters["limit"] = limit
#     filters["offset"] = offset

#     return frappe.db.sql(query, filters, as_dict=True)

@frappe.whitelist()
def fetch_all_gl_entries(
    from_date=None, to_date=None, company=None, account=None,
    cost_center=None, party_type=None, party=None, voucher_no=None,
    limit=1000, offset=0
):
    """
    Fetch GL entries with opening & closing balances, advanced filtering, pagination, and additional info.
    """
    conditions = ["gle.docstatus = 1", "IFNULL(gle.is_cancelled, 0) = 0"]
    filters = {}

    # --- Apply filters for main entries ---
    if company:
        conditions.append("gle.company = %(company)s")
        filters["company"] = company
    if account:
        conditions.append("gle.account = %(account)s")
        filters["account"] = account
    if cost_center:
        conditions.append("gle.cost_center = %(cost_center)s")
        filters["cost_center"] = cost_center
    if party_type:
        conditions.append("gle.party_type = %(party_type)s")
        filters["party_type"] = party_type
    if party:
        conditions.append("gle.party = %(party)s")
        filters["party"] = party
    if voucher_no:
        conditions.append("gle.voucher_no = %(voucher_no)s")
        filters["voucher_no"] = voucher_no
    if from_date:
        conditions.append("gle.posting_date >= %(from_date)s")
        filters["from_date"] = from_date
    if to_date:
        conditions.append("gle.posting_date <= %(to_date)s")
        filters["to_date"] = to_date

    where_clause = " AND ".join(conditions)

    # --- Main query for GL Entries ---
    entries_query = f"""
        SELECT
            gle.posting_date,
            gle.account,
            acc.account_name,
            gle.party_type,
            gle.party,
            IFNULL(cust.customer_name, IFNULL(supp.supplier_name, '')) AS party_name,
            cc.cost_center_name,
            gle.debit,
            gle.credit,
            gle.voucher_type,
            gle.voucher_no,
            gle.against_voucher,
            gle.against_voucher_type,
            proj.project_name,
            dept.department_name,
            gle.account_currency,
            gle.remarks,
            gle.company,
            gle.voucher_subtype,
            gle.against
        FROM `tabGL Entry` gle
        LEFT JOIN `tabAccount` acc ON acc.name = gle.account
        LEFT JOIN `tabCustomer` cust ON gle.party_type='Customer' AND gle.party = cust.name
        LEFT JOIN `tabSupplier` supp ON gle.party_type='Supplier' AND gle.party = supp.name
        LEFT JOIN `tabCost Center` cc ON cc.name = gle.cost_center
        LEFT JOIN `tabProject` proj ON proj.name = gle.project
        LEFT JOIN `tabDepartment` dept ON dept.name = gle.department
        WHERE {where_clause}
        ORDER BY gle.account ASC, gle.posting_date ASC, gle.creation ASC
        LIMIT %(limit)s OFFSET %(offset)s
    """

    # --- Opening Balance Query (before from_date) ---
    opening_filters = filters.copy()
    opening_conditions = ["gle.docstatus = 1", "IFNULL(gle.is_cancelled, 0) = 0"]

    if company:
        opening_conditions.append("gle.company = %(company)s")
    if account:
        opening_conditions.append("gle.account = %(account)s")
    if cost_center:
        opening_conditions.append("gle.cost_center = %(cost_center)s")
    if party_type:
        opening_conditions.append("gle.party_type = %(party_type)s")
    if party:
        opening_conditions.append("gle.party = %(party)s")

    if from_date:
        opening_conditions.append("gle.posting_date < %(from_date)s")

    opening_where = " AND ".join(opening_conditions)

    opening_query = f"""
        SELECT
            gle.account,
            acc.account_name,
            SUM(gle.debit) AS opening_debit,
            SUM(gle.credit) AS opening_credit,
            SUM(gle.debit - gle.credit) AS opening_balance
        FROM `tabGL Entry` gle
        LEFT JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE {opening_where}
        GROUP BY gle.account
    """

    # --- Closing Balance Query (up to to_date) ---
    closing_filters = filters.copy()
    closing_conditions = ["gle.docstatus = 1", "IFNULL(gle.is_cancelled, 0) = 0"]

    if company:
        closing_conditions.append("gle.company = %(company)s")
    if account:
        closing_conditions.append("gle.account = %(account)s")
    if cost_center:
        closing_conditions.append("gle.cost_center = %(cost_center)s")
    if party_type:
        closing_conditions.append("gle.party_type = %(party_type)s")
    if party:
        closing_conditions.append("gle.party = %(party)s")

    if to_date:
        closing_conditions.append("gle.posting_date <= %(to_date)s")

    closing_where = " AND ".join(closing_conditions)

    closing_query = f"""
        SELECT
            gle.account,
            acc.account_name,
            SUM(gle.debit) AS closing_debit,
            SUM(gle.credit) AS closing_credit,
            SUM(gle.debit - gle.credit) AS closing_balance
        FROM `tabGL Entry` gle
        LEFT JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE {closing_where}
        GROUP BY gle.account
    """

    # --- Execute Queries ---
    filters["limit"] = limit
    filters["offset"] = offset

    opening_balances = frappe.db.sql(opening_query, opening_filters, as_dict=True)
    closing_balances = frappe.db.sql(closing_query, closing_filters, as_dict=True)
    entries = frappe.db.sql(entries_query, filters, as_dict=True)

    return {
        "opening_balances": opening_balances,
        "entries": entries,
        "closing_balances": closing_balances
    }
