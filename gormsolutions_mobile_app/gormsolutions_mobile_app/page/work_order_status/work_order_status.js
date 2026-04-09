frappe.pages['work-order-status'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Work Order Status Overview',
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
            item_group: filters.item_group.get_value() || null
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.work_order_status_overview.get_work_order_status_overview",
            args: args,
            callback: function(r) {
                if (r.message && r.message.length) {
                    const data = r.message;

                    // Group items by work_order
                    const workOrders = {};
                    data.forEach(d => {
                        if (!workOrders[d.work_order]) {
                            workOrders[d.work_order] = {
                                info: d,
                                items: []
                            };
                        }
                        workOrders[d.work_order].items.push(d);
                    });

                    // Build HTML table
                    let html = `<table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Work Order</th>
                                <th>Item</th>
                                <th>Qty</th>
                                <th>Status</th>
                                <th>Planned Start</th>
                                <th>Planned End</th>
                                <th>Produced Qty</th>
                            </tr>
                        </thead>
                        <tbody>`;

                    Object.values(workOrders).forEach(wo => {
                        wo.items.forEach((item, idx) => {
                            html += `<tr>
                                <td>
                                    <a href="#" onclick="frappe.set_route('Form', 'Work Order', '${item.work_order}')">
                                        ${item.work_order}
                                    </a>
                                </td>
                                <td>${item.item_code} - ${item.item_name}</td>
                                <td style="text-align: right;">${item.required_qty.toLocaleString()}</td>
                                <td>${idx === 0 ? wo.info.status : ''}</td>
                                <td>${idx === 0 ? wo.info.planned_start_date : ''}</td>
                                <td>${idx === 0 ? wo.info.actual_end_date : ''}</td>
                                <td style="text-align: right;">${item.produced_qty.toLocaleString()}</td>
                            </tr>`;
                        });
                    });

                    html += `</tbody></table>`;
                    $('#report_area').html(html);
                } else {
                    $('#report_area').html('<p>No Work Orders found for selected filters.</p>');
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

    filters.item_group = page.add_field({
        label: 'Item Group', fieldtype: 'Link',
        options: 'Item Group',
        change: reload_data
    });

    // Area to display report
    page.body.append(`<div id="report_area" style="margin-top: 20px;"></div>`);

    // Add Print PDF button
    page.add_menu_item('Print PDF', function() {
        let report_html = document.getElementById('report_area').innerHTML;
        let w = window.open();
        w.document.write('<html><head><title>Work Order Status Overview</title>');
        w.document.write('<style>table{width:100%;border-collapse: collapse;} th, td{border:1px solid #000;padding:5px;text-align:left;} th{text-align:center;}</style>');
        w.document.write('</head><body>');
        w.document.write('<h3>Work Order Status Overview</h3>');
        w.document.write(report_html);
        w.document.write('</body></html>');
        w.document.close();
        w.print();
    });

    // Initial load
    reload_data();
};
