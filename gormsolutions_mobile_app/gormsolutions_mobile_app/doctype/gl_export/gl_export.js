// Copyright (c) 2025, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("GL Export", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('GL Export', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {

            // Button to download CSV directly (synchronous)
            frm.add_custom_button('Download GL Now', () => {
                frappe.call({
                    method: 'gormsolutions_mobile_app.gormsolutions_mobile_app.doctype.gl_export.gl_export.download_gl_export',
                    args: { docname: frm.doc.name },
                    callback: function(r) {
                        if (r.message && r.message.file_url) {
                            window.open(r.message.file_url);
                        } else {
                            frappe.msgprint("Failed to generate or find the file.");
                        }
                    }
                });
            });

            // Button to start background export (calls instance method)
            // frm.add_custom_button('Start Background Export', () => {
            //     frm.call('export_gl')
            //         .then(() => {
            //             frappe.msgprint("Export started in background.");
            //         })
            //         .catch(() => {
            //             frappe.msgprint("Failed to start export.");
            //         });
            // });

            // Button to cancel background export job
            // frm.add_custom_button('Cancel Export Job', () => {
            //     frappe.call({
            //         method: 'gormsolutions_mobile_app.gormsolutions_mobile_app.doctype.gl_export.gl_export.cancel_export_job',
            //         args: { docname: frm.doc.name },
            //         callback: function() {
            //             frappe.show_alert("Export job cancelled.");
            //             frm.reload_doc();
            //         }
            //     });
            // });
        }
    }
});

