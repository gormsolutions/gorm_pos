// Copyright (c) 2025, mututa paul and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Closing Shift', {
    onload(frm) {
        if (!frm.doc.user) {
            frm.set_value('user', frappe.session.user);
        }
    },

    pos_profile(frm) {
        if (!frm.doc.period_start_date || !frm.doc.period_end_date) {
            frappe.msgprint("Please set both Period Start Date and Period End Date.");
            return;
        }

        frappe.call({
            method: 'gormsolutions_mobile_app.custom_api.points.clossing_doc.fetch_pos_closing_data',
            args: {
                pos_profile: frm.doc.pos_profile,
                company: frm.doc.company,
                user: frm.doc.user || frappe.session.user,
                start_date: frm.doc.period_start_date,
                end_date: frm.doc.period_end_date,
                pos_opening_entry: frm.doc.pos_opening_entry || null
            },
            callback(r) {
                console.log(r);
                if (!r.message) return;
                const data = r.message;

                // Clear tables
                frm.clear_table('pos_transactions');
                frm.clear_table('payment_reconciliation');

                // Set POS Transactions
                (data.pos_transactions || []).forEach(row => {
                    frm.add_child('pos_transactions', row);
                });

                // Set Payment Reconciliation with difference calculation
                (data.payment_reconciliation || []).forEach(row => {
                    row.difference = flt(row.closing_amount) - flt(row.expected_amount);
                    frm.add_child('payment_reconciliation', row);
                });

                // Set totals
                frm.set_value('grand_total', data.grand_total || 0);
                frm.set_value('net_total', data.net_total || 0);
                frm.set_value('total_quantity', data.total_quantity || 0);

                // Refresh all fields
                frm.refresh_fields();
            }
        });
    }
});

frappe.ui.form.on('POS Closing Entry Detail', {
    closing_amount(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.difference = flt(row.closing_amount) - flt(row.expected_amount);
        frm.refresh_field('payment_reconciliation');
    }
});
