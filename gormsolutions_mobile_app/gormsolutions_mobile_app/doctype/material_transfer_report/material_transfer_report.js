frappe.ui.form.on('Material Transfer Report', {
    fetch_report: function(frm) {
        frm.clear_table("report_items");

        let filters = {
            ID: frm.doc.stock_transfer_id, 
            company: frm.doc.company,
            cost_center: frm.doc.cost_center,
            source_warehouse: frm.doc.source_warehouse,
            target_warehouse: frm.doc.target_warehouse,
            item_code: frm.doc.item_code,          // <-- new
            item_name: frm.doc.item_name,
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.gorm_insights.stock_transfer_report.get_material_transfer_report",
            args: { filters: filters },
            callback: function(r) {
                if(r.message && Array.isArray(r.message)) {
                    r.message.forEach(function(row) {
                        frm.add_child("report_items", {
                            id: row.ID,
                            status: row.Status,
                            stock_entry_type: row["Stock Entry Type"],
                            company: row.Company,
                            default_source_warehouse: row["Default Source Warehouse"],
                            default_target_warehouse: row["Default Target Warehouse"],
                            cost_center: row["Cost Center"],
                            item_code: row["Item Code"],      // <-- new
                            posting_date: row["Posting Date"],     // <-- new
                            posting_time: row["Posting Time"],     // <-- new
                            item_name: row["Item Name"],
                            stock_qty: row["Stock Qty"],
                            original_qty: row["Original Qty"],
                            accepted_qty: row["Accepted Qty"],
                            difference_qty: row["Difference Qty"]
                        });
                    });
                    frm.refresh_field("report_items");
                    frappe.msgprint(__('Report fetched successfully'));
                } else {
                    frappe.msgprint(__('No data found for the selected filters'));
                }
            }
        });
    },

    download_csv: function(frm) {
        let filters = {
            company: frm.doc.company,
            cost_center: frm.doc.cost_center,
            source_warehouse: frm.doc.source_warehouse,
            target_warehouse: frm.doc.target_warehouse,
            item_code: frm.doc.item_code,          // <-- new
            item_name: frm.doc.item_name,
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.gorm_insights.stock_transfer_report.get_material_transfer_report",
            args: { filters: filters, download: 1 },
            callback: function(r) {
                if(r.message && typeof r.message === "string") {
                    let blob = new Blob([r.message], { type: "text/csv;charset=utf-8;" });
                    let link = document.createElement("a");
                    link.href = URL.createObjectURL(blob);
                    link.download = "material_transfer_report.csv";
                    link.click();
                }
            }
        });
    }
});
