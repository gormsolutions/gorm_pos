import frappe
from frappe.model.naming import make_autoname
import re

def custom_autoname(doc, method):
    """
    Auto-name Sales Invoice:
        <COMPANY-ABBREV>-SINV-<CLEAN-COST-CENTER>-.MM./.YYYY.-
    """
    if not doc.company:
        frappe.throw("Company is required to generate the name.")

    if not doc.cost_center:
        frappe.throw("Cost Center is required to generate the name.")

    # 1. Company abbreviation
    company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
    if not company_abbr:
        frappe.throw(f"Abbreviation not found for company: {doc.company}")

    # 2. Clean cost-center string
    cost_center_code = doc.cost_center

    #    a) Remove everything except letters, digits, dash, dot, slash
    cost_center_code = re.sub(r"[^A-Za-z0-9\-\./]", "", cost_center_code)

    #    b) Remove company abbreviation (case-insensitive)
    cost_center_code = re.sub(
        re.escape(company_abbr), "", cost_center_code, flags=re.IGNORECASE
    )

    #    c) Collapse multiple dashes / trim
    cost_center_code = re.sub(r"-+", "-", cost_center_code).strip("-")

    # 3. Build naming-series pattern
    series_pattern = f"{company_abbr}-SINV-{cost_center_code}-.MM./.YYYY.-.#####"

    # 4. Ensure pattern is in naming_series options
    ensure_series_in_naming_field(series_pattern)

    # 5. Assign series & name
    doc.naming_series = series_pattern
    doc.name = make_autoname(series_pattern)


def ensure_series_in_naming_field(new_series: str):
    """Add the new series to Sales Invoice naming_series options if missing."""
    docfield = frappe.get_doc(
        "DocField", {"parent": "Sales Invoice", "fieldname": "naming_series"}
    )
    options = [opt.strip() for opt in (docfield.options or "").split("\n") if opt.strip()]

    if new_series not in options:
        options.append(new_series)
        docfield.options = "\n".join(options)
        docfield.save(ignore_permissions=True)
        frappe.clear_cache(doctype="Sales Invoice")
        frappe.msgprint(
            f"Added naming series '{new_series}' to Sales Invoice naming_series options"
        )