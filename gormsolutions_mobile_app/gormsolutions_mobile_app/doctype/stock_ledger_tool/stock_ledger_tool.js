// Copyright (c) 2025, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Stock Ledger Tool", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Stock Ledger Tool', {
    refresh: function (frm) {
        if (!frm.doc.__islocal) {

            // --- existing button ---
            frm.add_custom_button(__('Download Stock ledger'), () => {
                frappe.call({
                    method: "gormsolutions_mobile_app.custom_api.general_report.stock_ledger.export_stock_ledger",
                    args: {
                        filters: {
                            company: frm.doc.company,
                            from_date: frm.doc.from_date,
                            to_date: frm.doc.to_date,
                            warehouse: frm.doc.warehouse,
                            item_group: frm.doc.item_group,
                            item_code: frm.doc.item_code
                        }
                    },
                    callback: (r) => {
                        if (r.message) {
                            window.open(r.message.file_url, "_blank");
                        }
                    }
                });
            });

            // --- new Stock Balance button ---
            frm.add_custom_button(__('Download Stock Balance'), () => {
                frappe.call({
                    method: "gormsolutions_mobile_app.custom_api.general_report.stock_balance.export_stock_balance",
                    args: {
                        filters: {
                            company: frm.doc.company,
                            from_date: frm.doc.from_date,
                            to_date: frm.doc.to_date,
                            warehouse: frm.doc.warehouse,
                            item_group: frm.doc.item_group,
                            item_code: frm.doc.item_code
                        }
                    },
                    callback: (r) => {
                        if (r.message) {
                            window.open(r.message.file_url, "_blank");
                        }
                    }
                });
            });

        }
    }
});