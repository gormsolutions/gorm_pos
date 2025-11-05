frappe.pages['bom-cost-variance'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'BOM Cost Variance',
        single_column: true
    });

    let filters = {};
    let today = frappe.datetime.get_today();

    function reload_data() {
        let args = {
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value(),
            company: filters.company.get_value() || null,
            cost_center: filters.cost_center.get_value() || null,
            item: filters.item.get_value() || null
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.bom_cost_variance.get_bom_cost_variance",
            args: args,
            callback: function(r) {
                if (r.message) {
                    let data = r.message;
                    let html = `<table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th>Qty</th>
                                <th>Actual Rate</th>
                                <th>BOM Rate</th>
                                <th>Variance</th>
                                <th>Variance %</th>
                            </tr>
                        </thead>
                        <tbody>`;

                    data.forEach(d => {
                        html += `<tr>
                            <td>${d.item_code} - ${d.item_name}</td>
                            <td style="text-align: right;">${d.qty.toLocaleString()}</td>
                            <td style="text-align: right;">${d.actual_rate.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td style="text-align: right;">${d.bom_rate.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td style="text-align: right;">${d.variance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td style="text-align: right;">${d.variance_percent.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}%</td>
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

    filters.cost_center = page.add_field({
        label: 'Cost Center', fieldtype: 'Link',
        options: 'Cost Center',
        change: reload_data
    });

    filters.item = page.add_field({
        label: 'Item', fieldtype: 'Link',
        options: 'Item',
        change: reload_data
    });

    // Area to display report
    page.body.append(`<div id="report_area" style="margin-top: 20px;"></div>`);

    // Add Print PDF button
    page.add_menu_item('Print PDF', function() {
        let report_html = document.getElementById('report_area').innerHTML;
        let w = window.open();
        w.document.write('<html><head><title>BOM Cost Variance</title>');
        w.document.write('<style>table{width:100%;border-collapse: collapse;} th, td{border:1px solid #000;padding:5px;text-align:left;} th{text-align:center;}</style>');
        w.document.write('</head><body>');
        w.document.write('<h3>BOM Cost Variance</h3>');
        w.document.write(report_html);
        w.document.write('</body></html>');
        w.document.close();
        w.print();
    });

    // Initial load
    reload_data();
}
