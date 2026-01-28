// Copyright (c) 2026, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Vehicle Income", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on('Vehicle Income', {
    refresh(frm) {
        if (!frm.doc.sales_invoice) {
            frm.add_custom_button(__('Submit & Invoice'), () => {
                frm.call({
                    method: 'submit_and_invoice',
                    freeze: true,
                    callback(r) {
                        if (r.message) {
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
    }
});
