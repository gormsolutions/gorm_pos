import frappe
import json


@frappe.whitelist()
def fetchy_all_gl_entries(
    from_date, to_date, company,
    account=None, cost_center=None,
    party_type=None, party=None,
    voucher_type=None, voucher_no=None,
    limit=100, last_name=None,
    last_date=None,
    categorize_by=None
):

    limit = int(limit or 100)

    # -------------------------------------------------
    # NORMALIZE LISTS
    # -------------------------------------------------
    def normalize_list(value):
        if not value:
            return None

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except:
                pass

            if "," in value:
                return [v.strip() for v in value.split(",") if v.strip()]

            return [value.strip()]

        if isinstance(value, (list, tuple)):
            return list(value)

        return None

    accounts = normalize_list(account)
    cost_centers = normalize_list(cost_center)
    voucher_types = normalize_list(voucher_type)
    parties = normalize_list(party)

    # -------------------------------------------------
    # BASE FILTERS (NO DATE HERE - ERPNext STYLE)
    # -------------------------------------------------
    filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "party_type": party_type,
        "voucher_no": voucher_no,
    }

    base_cond = [
        "gle.company = %(company)s",
        "gle.is_cancelled = 0",
        "gle.docstatus = 1"
    ]

    def build_in(field, values):
        if not values:
            return

        placeholders = []
        for i, v in enumerate(values):
            key = f"{field}_{i}"
            filters[key] = v
            placeholders.append(f"%({key})s")

        base_cond.append(f"gle.{field} IN ({', '.join(placeholders)})")

    build_in("account", accounts)
    build_in("cost_center", cost_centers)
    build_in("voucher_type", voucher_types)
    build_in("party", parties)

    if party_type:
        base_cond.append("gle.party_type = %(party_type)s")

    if voucher_no:
        base_cond.append("gle.voucher_no = %(voucher_no)s")

    # Build WHERE without pagination (for balances and total count)
    balance_where_clause = " AND ".join(base_cond)

    # pagination (entries only)
    if last_date and last_name:
        base_cond.append("(gle.posting_date, gle.name) > (%(last_date)s, %(last_name)s)")
        filters["last_date"] = last_date
        filters["last_name"] = last_name

    where_clause = " AND ".join(base_cond)

    # -------------------------------------------------
    # ENTRIES (DATE RANGE ONLY HERE)
    # -------------------------------------------------
    entries = frappe.db.sql(f"""
        SELECT
            gle.name,
            gle.posting_date,
            gle.voucher_type,
            gle.voucher_no,
            gle.account,
            acc.account_name,
            gle.party_type,
            gle.party,
            IFNULL(cust.customer_name, IFNULL(supp.supplier_name, '')) AS party_name,
            gle.remarks,
            gle.debit,
            gle.credit,
            gle.cost_center,
            cc.cost_center_name
        FROM `tabGL Entry` gle
        LEFT JOIN `tabAccount` acc ON acc.name = gle.account
        LEFT JOIN `tabCustomer` cust ON gle.party_type = 'Customer' AND gle.party = cust.name
        LEFT JOIN `tabSupplier` supp ON gle.party_type = 'Supplier' AND gle.party = supp.name
        LEFT JOIN `tabCost Center` cc ON cc.name = gle.cost_center
        WHERE {where_clause}
        AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY gle.posting_date ASC, gle.name ASC
        LIMIT {limit}
    """, filters, as_dict=True)

    # -------------------------------------------------
    # TOTAL COUNT
    # -------------------------------------------------
    total_count = frappe.db.sql(f"""
        SELECT COUNT(*) AS total
        FROM `tabGL Entry` gle
        WHERE {balance_where_clause}
        AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
    """, filters, as_dict=True)[0].total

    # -------------------------------------------------
    # OPENING + CLOSING BALANCE (ERPNext STYLE)
    # -------------------------------------------------
    balance_data = frappe.db.sql(f"""
        SELECT
            SUM(CASE WHEN gle.posting_date < %(from_date)s THEN gle.debit ELSE 0 END) AS opening_debit,
            SUM(CASE WHEN gle.posting_date < %(from_date)s THEN gle.credit ELSE 0 END) AS opening_credit,
            SUM(CASE WHEN gle.posting_date < %(from_date)s THEN (gle.debit - gle.credit) ELSE 0 END) AS opening_balance,

            SUM(CASE WHEN gle.posting_date <= %(to_date)s THEN gle.debit ELSE 0 END) AS closing_debit,
            SUM(CASE WHEN gle.posting_date <= %(to_date)s THEN gle.credit ELSE 0 END) AS closing_credit,
            SUM(CASE WHEN gle.posting_date <= %(to_date)s THEN (gle.debit - gle.credit) ELSE 0 END) AS closing_balance
        FROM `tabGL Entry` gle
        WHERE {balance_where_clause}
    """, filters, as_dict=True)[0]

    # -------------------------------------------------
    # GROUPING
    # -------------------------------------------------
    for e in entries:

        if categorize_by == "Categorize by Voucher":
            e.group_key = f"{e.voucher_type}-{e.voucher_no}"

        elif categorize_by == "Categorize by Voucher (Consolidated)":
            e.group_key = e.voucher_no

        elif categorize_by == "Categorize by Account":
            e.group_key = f"{e.account}-{e.account_name}"

        elif categorize_by == "Categorize by Party":
            e.group_key = f"{e.party_type}-{e.party}"

        else:
            e.group_key = "All"

        e.debit = round(e.debit or 0, 2)
        e.credit = round(e.credit or 0, 2)

    # -------------------------------------------------
    # RESPONSE
    # -------------------------------------------------
    return {
        "entries": entries,
        "total_count": total_count,

        "opening_debit": round(balance_data.opening_debit or 0, 2),
        "opening_credit": round(balance_data.opening_credit or 0, 2),
        "opening_balance": round(balance_data.opening_balance or 0, 2),

        "closing_debit": round(balance_data.closing_debit or 0, 2),
        "closing_credit": round(balance_data.closing_credit or 0, 2),
        "closing_balance": round(balance_data.closing_balance or 0, 2),
    }