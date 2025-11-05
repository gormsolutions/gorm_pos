frappe.pages['sales-by-product-cat'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales by Product Category',
        single_column: true
    });

    // Filters
    let filters = {};
    let today = frappe.datetime.get_today();

    function reload_data() {
        let args = {
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value(),
            company: filters.company.get_value() || null,
            cost_center: filters.cost_center.get_value() || null,
            customer: filters.customer.get_value() || null,
            item_group: filters.item_group.get_value() || null  // <-- Item Group filter
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.selling_by_category.get_sales_by_category",
            args: args,
            callback: function(r) {
                if (r.message) {
                    let data = r.message;
                    let html = `<table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Product Category</th>
                                <th>Total Sales</th>
                                <th>Invoice Count</th>
                            </tr>
                        </thead>
                        <tbody>`;

                    data.forEach(d => {
                        html += `<tr>
                            <td>${d.product_category}</td>
                            <td style="text-align: right;">${d.total_sales.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td style="text-align: right;">${d.invoice_count.toLocaleString()}</td>
                        </tr>`;
                    });

                    html += `</tbody></table>`;
                    $('#report_area').html(html);
                }
            }
        });
    }

    // Add filter fields
    filters.from_date = page.add_field({
        label: 'From Date', fieldtype: 'Date',
        default: today, reqd: 1, change: reload_data
    });

    filters.to_date = page.add_field({
        label: 'To Date', fieldtype: 'Date',
        default: today, reqd: 1, change: reload_data
    });

    filters.company = page.add_field({
        label: 'Company', fieldtype: 'Link',
        options: 'Company',
        default: frappe.defaults.get_default("Company"),
        change: reload_data
    });

    filters.sales_rep = page.add_field({
        label: 'Sales Rep', fieldtype: 'Link',
        options: 'Sales Person',
        change: reload_data
    });

    filters.cost_center = page.add_field({
        label: 'Cost Center', fieldtype: 'Link',
        options: 'Cost Center',
        change: reload_data
    });

    filters.customer = page.add_field({
        label: 'Customer', fieldtype: 'Link',
        options: 'Customer',
        change: reload_data
    });

    filters.item_group = page.add_field({
        label: 'Product Category', fieldtype: 'Link',
        options: 'Item Group',
        change: reload_data
    });

    // Area to display report
    page.body.append(`<div id="report_area" style="margin-top: 20px;"></div>`);

    // Initial load
    reload_data();
}
