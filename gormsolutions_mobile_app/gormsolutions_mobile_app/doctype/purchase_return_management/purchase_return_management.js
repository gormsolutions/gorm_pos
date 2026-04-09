frappe.ui.form.on('Purchase Return Management', {
    refresh: function(frm) {
        populate_invoices(frm)
        // CreatePurchaseInvoice(frm)
        calculateTotals(frm)

    },
    supplier: function(frm) {
        populate_invoices(frm)
        get_invoice_items(frm)
    },
    date: function(frm) {
        populate_invoices(frm)
        get_invoice_items(frm)
    },
    posting_date: function(frm) {
        populate_invoices(frm)
        get_invoice_items(frm)
        calculateTotals(frm)
    },

    reference_purchase_invoice: function(frm) {
        get_invoice_items(frm)
    }
 
});



// Function to create a new Purchase Invoice (Positive Transaction)
function get_invoice_items(frm) {
    if (frm.doc.reference_purchase_invoice) {
        // Get the reference Purchase Invoice selected
        let purchase_invoice = frm.doc.reference_purchase_invoice;

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.purchase_return_management.get_invoice_items",  // Adjust the path as per your app structure
            args: {
                purchase_invoice: purchase_invoice
            },
            callback: function(r) {
                if (r.message) {
                    // Clear any existing items in the return_items table
                    frm.clear_table("return_items");

                    // Loop through each item in the purchase invoice and add to the return_items table
                    r.message.items.forEach(function(item) {
                        console.log(item)
                        let new_row = frm.add_child("return_items");
                        new_row.item_code = item.item_code;
                        new_row.qty = item.qty;
                        new_row.rate = item.rate;
                        new_row.amount = item.qty * item.rate;
                        new_row.uom = item.uom;
                        new_row.warehouse = item.warehouse;
                    });

                    // Set the posting date in the form
                    frm.set_value("invoice_date", r.message.posting_date);
                    frm.set_value("status", r.message.status);
                    frm.set_value("return_against", r.message.return_against);

                    frm.refresh_field("return_items");
                    frm.refresh_field("invoice_date");
                    frm.refresh_field("status");
                    frm.refresh_field("return_against");
                }
            }
        });
    } else {
        // If no invoice is selected, clear the child table and posting date field
        frm.clear_table("return_items");
        frm.set_value("posting_date", null);
        frm.refresh_field("return_items");
        frm.refresh_field("invoice_date");
        frm.refresh_field("status");
        frm.refresh_field("return_against");
    }
}


// Function to create a Debit Note (Purchase Invoice Return)
function populate_invoices(frm) {
    if (frm.doc.supplier) {
        // Check if from_date is selected
        let from_date = frm.doc.date;  // Assuming 'from_date' is the field holding the selected date
        let filters = {
            supplier: frm.doc.supplier,
            docstatus: 1,  // Only fetch active invoices (not cancelled)
            status: "Return",  // Only fetch invoices with 'Return' status
            custom_suplier_return_status: ["!=", "Items Compensated"] // Corrected syntax for "not equal to"
        };

        // Add date filter if 'from_date' is provided
        if (from_date) {
            filters["posting_date"] = [">=", from_date];  // Filter invoices posted on or after the selected date
        }

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Purchase Invoice",
                filters: filters,
                fields: ["name"],
                order_by: "posting_date desc"
            },
            callback: function(r) {
                console.log("Fetched Purchase Invoices:", r.message);
                if (r.message && r.message.length > 0) {
                    let options = r.message.map(inv => inv.name); // Get names as list
                    frm.set_df_property("reference_purchase_invoice", "options", options);
                    frm.refresh_field("reference_purchase_invoice");
                } else {
                    frm.set_df_property("reference_purchase_invoice", "options", []);
                    frm.refresh_field("reference_purchase_invoice");
                }
            }
        });
    } else {
        frm.set_df_property("reference_purchase_invoice", "options", []);
        frm.refresh_field("reference_purchase_invoice");
    }
}

frappe.ui.form.on('Return Items', {
    amount: function(frm, cdt, cdn) {
        calculateTotals(frm);
    }
});
function calculateTotals(frm) {
    var total_amount = 0;
    frm.doc.return_items.forEach(function(item) {
        total_amount += item.amount;
    });
    frm.set_value('grand_total', total_amount);
    refresh_field('grand_total');
}


