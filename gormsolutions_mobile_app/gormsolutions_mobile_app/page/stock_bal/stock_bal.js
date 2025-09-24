frappe.pages['stock-bal'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Stock Balance',
        single_column: true
    });

    // filters
    let filters = {};

    filters.company = page.add_field({
        label: 'Company',
        fieldtype: 'Link',
        options: 'Company',
        reqd: 1
    });

    filters.item_group = page.add_field({
        label: 'Item Group',
        fieldtype: 'Link',
        options: 'Item Group'
    });

    filters.warehouse = page.add_field({
        label: 'Warehouse',
        fieldtype: 'Link',
        options: 'Warehouse'
    });

    // Button
    page.add_inner_button(__('Load Data'), function() {
        load_stock_data(filters, wrapper);
    });
};

function load_stock_data(filters, wrapper) {
    frappe.call({
        method: "gormsolutions_mobile_app.custom_api.reports.stock_balance.get_stock_balances_cursor",
        args: {
            company: filters.company.get_value(),
            item_group: filters.item_group.get_value(),
            warehouse: filters.warehouse.get_value(),
            page_size: 200
        },
        callback: function(r) {
            if (r.message) {
                console.log(r.message); // render to table
            }
        }
    });
}
