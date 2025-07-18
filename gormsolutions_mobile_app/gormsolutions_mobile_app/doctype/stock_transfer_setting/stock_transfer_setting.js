// Copyright (c) 2025, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Stock Transfer Setting", {
// 	refresh(frm) {

// 	},
// });apps/gormsolutions_mobile_app////.py

frappe.ui.form.on("Stock Transfer Setting", {
    refresh: function (frm) {
        frm.add_custom_button("Create User Permissions", function () {
            frappe.call({
                method: "gormsolutions_mobile_app.custom_api.stock.stock_transfer_setting.create_user_permissions_from_stock_transfer_setting",
                args: {
                    docname: "cor2rokmld"
                },
                callback: function (r) {
                    if (!r.exc) {
                        frappe.msgprint("User Permissions created successfully");
                    }
                }
            });
        });
    }
});

