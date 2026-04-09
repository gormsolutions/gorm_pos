frappe.pages['revenue-trends'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'YoY & MoM Revenue Trends',
        single_column: true
    });

    // 🔹 Filters
    let filters = {};
    let today = frappe.datetime.now_date();

    filters.from_date = page.add_field({
        label: 'From Date',
        fieldtype: 'Date',
        default: frappe.datetime.add_months(today, -6),
        change: reload_items
    });

    filters.to_date = page.add_field({
        label: 'To Date',
        fieldtype: 'Date',
        default: today,
        change: reload_items
    });

    filters.company = page.add_field({
        label: 'Company',
        fieldtype: 'Link',
        options: 'Company',
        default: frappe.defaults.get_default("Company"),
        change: reload_items
    });

    filters.customer = page.add_field({
        label: 'Customer',
        fieldtype: 'Link',
        options: 'Customer',
        reqd: 0,
        change: reload_items
    });

    filters.cost_center = page.add_field({
        label: 'Cost Center',
        fieldtype: 'Link',
        options: 'Cost Center',
        reqd: 0,
        change: reload_items
    });

    filters.period = page.add_field({
        label: 'Period',
        fieldtype: 'Select',
        options: ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'],
        default: 'Monthly',
        change: reload_items
    });

    // 🔹 Chart + Table
    $(`<div class="p-4 space-y-4">
        <div id="chart-area" style="height:350px;"></div>
        <div class="d-flex justify-end mb-2">
            <button class="btn btn-secondary btn-sm" id="download_excel">Download Excel</button>
            <button class="btn btn-secondary btn-sm ml-2" id="print_report">Print</button>
        </div>
        <div id="data-table" class="mt-4"></div>
    </div>`).appendTo(page.body);

    function reload_items() {
        const f = {
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value(),
            company: filters.company.get_value(),
            customer: filters.customer.get_value(),
            cost_center: filters.cost_center.get_value(),
            period: filters.period.get_value()
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.revenue_trends.get_yoy_mom_revenue",
            args: { filters: f },
            freeze: true,
            freeze_message: __("Fetching Revenue Trends..."),
            callback: function(r) {
                if(!r.message || !r.message.length){
                    $('#chart-area').html("<p class='text-muted text-center mt-4'>No data found.</p>");
                    $('#data-table').empty();
                    return;
                }

                const data = r.message;
                const labels = [...new Set(data.map(d=>d.period_label))];
                const revenue = data.map(d=>d.revenue);

                // Chart
                new frappe.Chart("#chart-area", {
                    title: "Revenue Trends",
                    data: { labels: labels, datasets: [{name:"Revenue", values: revenue}] },
                    type: 'bar',
                    height: 300,
                    colors: ['#2490ef']
                });

                // Table
                let html = `<table class="table table-bordered table-sm">
                    <thead>
                        <tr>
                            <th>Period</th>
                            <th>Cost Center</th>
                            <th>Revenue</th>
                            <th>MoM Growth %</th>
                            <th>YoY Growth %</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(d=>`
                            <tr>
                                <td>${d.period_label}</td>
                                <td>${d.cost_center || '-'}</td>
                                <td>${format_currency(d.revenue)}</td>
                                <td>${(d.mom_growth||0).toFixed(1)}%</td>
                                <td>${(d.yoy_growth||0).toFixed(1)}%</td>
                            </tr>`).join('')}
                    </tbody>
                </table>`;
                $('#data-table').html(html);

                // Download Excel
                $('#download_excel').off('click').on('click', function() {
                    frappe.tools.downloadify({
                        filename: `Revenue-Trends-${today}.csv`,
                        data: data.map(d => ({
                            Period: d.period_label,
                            Cost_Center: d.cost_center,
                            Revenue: d.revenue,
                            MoM_Growth: (d.mom_growth||0).toFixed(1),
                            YoY_Growth: (d.yoy_growth||0).toFixed(1)
                        }))
                    });
                });

                // Print
                $('#print_report').off('click').on('click', function() {
                    let w = window.open();
                    w.document.write('<pre>'+$('#data-table').html()+'</pre>');
                    w.print();
                    w.close();
                });
            }
        });
    }

    reload_items();
};
