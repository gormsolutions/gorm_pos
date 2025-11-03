// Copyright (c) 2025, mututa paul and contributors
// For license information, please see license.txt

frappe.ui.form.on('User Financial Report', {
    refresh: function (frm) {
        frm.add_custom_button(__('View Financial Report'), function () {
            const { user_email, from_date, to_date } = frm.doc;

            frappe.call({
                method: 'gormsolutions_mobile_app.custom_api.reports.user_financial_totals.get_user_financial_totals',
                args: { user_email, from_date, to_date },
                callback: function (r) {
                    if (r.message) {
                        const { data, totals } = r.message;
                        const formatCurrency = (value) => frappe.format(value, { fieldtype: 'Currency' });

                        let report_html = `
                            <center>
                                <h3>User's Daily Financial Report</h3>
                                <p><strong>User:</strong> ${r.message.user}</p>
                                <p><strong>From Date:</strong> ${r.message.from_date}</p>
                                <p><strong>To Date:</strong> ${r.message.to_date}</p>
                            </center>
                        `;

                        // Accounts summary
                        const generateAccountsSummaryTable = (accounts_summary) => {
                            if (!accounts_summary || Object.keys(accounts_summary).length === 0) {
                                return `<p>No accounts summary available.</p>`;
                            }
                            let table_html = `
                                <h4>Accounts Summary</h4>
                                <table class="table table-bordered" style="width:100%; border-collapse: collapse;">
                                    <thead><tr><th>Account</th><th>Amount</th></tr></thead>
                                    <tbody>
                            `;
                            Object.keys(accounts_summary).forEach(account => {
                                const amount = accounts_summary[account];
                                table_html += `<tr><td>${account}</td><td>${formatCurrency(amount)}</td></tr>`;
                            });
                            table_html += `</tbody></table>`;
                            return table_html;
                        };
                        report_html += generateAccountsSummaryTable(data.accounts_summary);

                        // Expense summary
                        const generateExpenseSummaryTable = (expense_summary) => {
                            if (!expense_summary || Object.keys(expense_summary).length === 0) {
                                return `<p>No Expense summary available.</p>`;
                            }
                            let table_html = `
                                <h4>Expense Summary</h4>
                                <table class="table table-bordered" style="width:100%; border-collapse: collapse;">
                                    <thead><tr><th>Account</th><th>Amount</th></tr></thead>
                                    <tbody>
                            `;
                            Object.keys(expense_summary).forEach(account => {
                                const amount = expense_summary[account];
                                table_html += `<tr><td>${account}</td><td>${formatCurrency(amount)}</td></tr>`;
                            });
                            table_html += `</tbody></table>`;
                            return table_html;
                        };
                        report_html += generateExpenseSummaryTable(data.expense_summary);

                        // Dynamic table section generator with counts and clickable invoice links
                        const generateTableSection = (title, records, columns) => {
                            if (!records.length) return `<p>No ${title}.</p>`;

                            let table_html = `
                                <h4>${title} (Total: ${records.length})</h4>
                                <table class="table table-bordered" style="width:100%; border-collapse: collapse;">
                                    <thead><tr>${columns.map(c => `<th>${c}</th>`).join('')}</tr></thead>
                                    <tbody>
                            `;

                            records.forEach(rec => {
                                table_html += `<tr>${columns.map(c => {
                                    let key = c.toLowerCase().replace(/ /g, '_');
                                    let val = rec[key];

                                    // Make invoice 'name' clickable
                                    if ((title === "Sales Invoices" || title === "Purchase Invoices") && key === "name" && val) {
                                        val = `<a href="https://erp.divacakes.com.ng/app/${title === "Sales Invoices" ? "sales-invoice" : "purchase-invoice"}/${encodeURIComponent(val)}" target="_blank">${val}</a>`;
                                    } else if (typeof val === 'number') {
                                        val = formatCurrency(val);
                                    } else if (c === 'Posting Time' && typeof val === 'string') {
                                        val = val.substring(0, 8);
                                    }

                                    return `<td>${val || ''}</td>`;
                                }).join('')}</tr>`;
                            });

                            table_html += `</tbody></table>`;
                            return table_html;
                        };

                        // Total expenses calculation
                        let totalExpenses = 0;
                        if (data.expense_summary && Object.keys(data.expense_summary).length > 0) {
                            Object.values(data.expense_summary).forEach(amount => {
                                totalExpenses += amount;
                            });
                        }

                        // Add all sections
                        report_html += generateTableSection("Advance Payment Received", data.received_payments, ['Party', 'Paid Amount', 'Posting Date']);
                        report_html += generateTableSection("Paid Payments", data.paid_payments, ['Party', 'Paid Amount', 'Posting Date']);
                        report_html += generateTableSection("Internal Transfers", data.internal_transfers, ['Name', 'Amount', 'Posting Date']);
                        report_html += generateTableSection("Sales Invoices", data.sales_invoices, ['Customer', 'name','Grand Total', 'Outstanding Amount', 'Collected Amount', 'Posting Time']);
                        report_html += generateTableSection("Purchase Invoices", data.purchase_invoices, ['Supplier', 'name', 'Grand Total', 'Outstanding Amount', 'Paid Value', 'Posting Date']);

                        // Financial totals
                        const totalFields = [
                            { label: 'Total Sales Amount', value: totals.total_sales_amount || 0 },
                            { label: 'Total Outstanding Sales', value: totals.total_sales_outstanding || 0 },
                            { label: 'Total Advance Payments Received', value: totals.total_received_payments || 0 },
                            { label: 'Total Collected Sales', value: totals.total_collected_sales_amount || 0 },
                            { label: 'Less : Total Amount Loyalty Points Redeemed', value: totals.total_loyalty_amount || 0 },
                            { label: 'Received + Collected Sales (POS)', value: totals.grand_received_amount || 0 },
                            { label: 'Total Internal Transfer Amount', value: totals.total_internal_transfer_amount || 0 },
                            { label: 'Total Purchase Amount', value: totals.total_purchase_amount || 0 },
                            { label: 'Total Paid PINV(POS) Amount', value: totals.total_paid_purchase_amount || 0 },
                            { label: 'Total Direct Payments to Suppliers', value: totals.total_paid_amount_to_suppliers || 0 },
                            { label: 'PINV(POS) + Direct Payments', value: totals.grand_paid_purchase_amount || 0 },
                            { label: 'Total Expenses', value: totalExpenses || 0 }
                        ];

                        let hasTotals = false;
                        report_html += `<h4>Financial Totals</h4><table class="table table-bordered" style="width:100%; border-collapse: collapse;"><tbody>`;
                        totalFields.forEach(item => {
                            if (item.value && item.value !== 0) {
                                hasTotals = true;
                                report_html += `<tr><td>${item.label}</td><td style="text-align: right">${formatCurrency(item.value)}</td></tr>`;
                            }
                        });
                        if (!hasTotals) report_html += `<tr><td colspan="2">No financial totals available.</td></tr>`;
                        report_html += `</tbody></table>`;

                        // Show modal with report
                        const report_modal = new frappe.ui.Dialog({
                            title: __('Financial Report'),
                            fields: [{ fieldtype: 'HTML', label: __('Report Content'), fieldname: 'report_content', options: report_html }],
                            size: 'extra-large',
                            primary_action_label: 'Print Report',
                            primary_action: () => {
                                const printWindow = window.open('', '', 'width=900,height=650');
                                printWindow.document.write(`
                                    <html><head>
                                    <title>Financial Report</title>
                                    <style>
                                        body { font-family: Arial, sans-serif; margin: 20px; }
                                        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                                        th, td { border: 1px solid #333; padding: 8px; text-align: left; }
                                        th { background-color: #f0f0f0; }
                                        h3, h4 { margin-top: 20px; }
                                    </style>
                                    </head>
                                    <body>${report_html}</body></html>
                                `);
                                printWindow.document.close();
                                printWindow.print();
                            }
                        });
                        report_modal.show();
                    }
                }
            });
        });
    }
});
