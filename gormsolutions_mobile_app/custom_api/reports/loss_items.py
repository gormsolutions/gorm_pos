import frappe         

@frappe.whitelist()
def get_loss_selling_items():
    data = frappe.db.sql("""
        SELECT
            sii.item_code,
            sii.item_name,
            sii.uom AS sales_uom,
            i.stock_uom AS default_uom,

            COALESCE(
                NULLIF(i.valuation_rate, 0),
                (
                    SELECT sri.valuation_rate
                    FROM `tabStock Reconciliation Item` sri
                    INNER JOIN `tabStock Reconciliation` sr
                        ON sr.name = sri.parent
                    WHERE
                        sri.item_code = sii.item_code
                        AND sr.docstatus = 1
                    ORDER BY sr.posting_date DESC, sr.posting_time DESC
                    LIMIT 1
                )
            ) AS valuation_rate_default_uom,

            COALESCE(uomcf.conversion_factor, 1) AS conversion_factor,

            (
                COALESCE(
                    NULLIF(i.valuation_rate, 0),
                    (
                        SELECT sri.valuation_rate
                        FROM `tabStock Reconciliation Item` sri
                        INNER JOIN `tabStock Reconciliation` sr
                            ON sr.name = sri.parent
                        WHERE
                            sri.item_code = sii.item_code
                            AND sr.docstatus = 1
                        ORDER BY sr.posting_date DESC, sr.posting_time DESC
                        LIMIT 1
                    )
                ) * COALESCE(uomcf.conversion_factor, 1)
            ) AS valuation_rate_sales_uom,

            sii.rate AS selling_rate,

            (
                (
                    COALESCE(
                        NULLIF(i.valuation_rate, 0),
                        (
                            SELECT sri.valuation_rate
                            FROM `tabStock Reconciliation Item` sri
                            INNER JOIN `tabStock Reconciliation` sr
                                ON sr.name = sri.parent
                            WHERE
                                sri.item_code = sii.item_code
                                AND sr.docstatus = 1
                            ORDER BY sr.posting_date DESC, sr.posting_time DESC
                            LIMIT 1
                        )
                    ) * COALESCE(uomcf.conversion_factor, 1)
                ) - sii.rate
            ) AS loss_amount

        FROM
            `tabSales Invoice Item` sii
        INNER JOIN
            `tabSales Invoice` si ON si.name = sii.parent
        INNER JOIN
            `tabItem` i ON i.name = sii.item_code
        LEFT JOIN
            `tabUOM Conversion Detail` uomcf
                ON uomcf.parent = i.name
                AND uomcf.uom = sii.uom

        WHERE
            si.docstatus = 1

        HAVING
            valuation_rate_sales_uom IS NOT NULL
            AND valuation_rate_sales_uom > selling_rate
    """, as_dict=True)

    return {
        "status": "success",
        "count": len(data),
        "data": data
    }
