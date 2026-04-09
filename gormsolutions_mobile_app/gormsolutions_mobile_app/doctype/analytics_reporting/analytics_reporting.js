// Copyright (c) 2025, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Analytics Reporting", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("Analytics Reporting", {
    refresh(frm) {
        frm.add_custom_button(__('Download Deleted Sales Invoices PDF'), function() {
            // Prompt user for a date range
            frappe.prompt([
                {
                    fieldname: 'from_date',
                    label: 'From Date',
                    fieldtype: 'Date',
                    reqd: 1
                },
                {
                    fieldname: 'to_date',
                    label: 'To Date',
                    fieldtype: 'Date',
                    reqd: 1
                }
            ],
            function(values){
                // Load html2pdf.js dynamically
                frappe.require("https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js", function() {
                    frappe.call({
                        method: "gormsolutions_mobile_app.custom_api.sales_invoice.reporting_issues.get_deleted_sales_invoices_html",
                        args: { 
                            from_date: values.from_date, 
                            to_date: values.to_date 
                        },
                        callback: function(r) {
                            if (r.message) {
                                // Create a hidden div for HTML
                                const container = document.createElement("div");
                                container.innerHTML = r.message;

                                // Optional: Add some PDF styling
                                container.style.fontFamily = "Arial, sans-serif";
                                container.style.fontSize = "12px";
                                container.querySelectorAll("table").forEach(tbl => {
                                    tbl.style.width = "100%";
                                    tbl.style.borderCollapse = "collapse";
                                });
                                container.querySelectorAll("th, td").forEach(cell => {
                                    cell.style.border = "1px solid #ddd";
                                    cell.style.padding = "4px";
                                });
                                container.querySelectorAll("th").forEach(th => {
                                    th.style.backgroundColor = "#f2f2f2";
                                });

                                document.body.appendChild(container);

                                // Generate PDF
                                html2pdf().from(container).set({
                                    margin: 10,
                                    filename: `deleted_sales_invoices_${values.from_date}_to_${values.to_date}.pdf`,
                                    html2canvas: { scale: 2 },
                                    jsPDF: { unit: "mm", format: "a4", orientation: "portrait" }
                                }).save().then(() => {
                                    document.body.removeChild(container);
                                    frappe.msgprint(__('PDF downloaded successfully'));
                                });
                            } else {
                                frappe.msgprint(__('No deleted invoices found for this period'));
                            }
                        }
                    });
                });
            },
            __('Filter Deleted Invoices'),
            __('Generate PDF'));
        });
    }
});
