frappe.pages['revenue-vs-target'].on_page_load = function (wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Revenue vs Target',
        single_column: true
    });

    // 🔹 Filters Setup
    let filters = {};
    let today = frappe.datetime.now_date();

    filters.from_date = page.add_field({
        label: 'From Date',
        fieldtype: 'Date',
        default: frappe.datetime.add_months(today, -1),
        change: () => reload_items()
    });

    filters.to_date = page.add_field({
        label: 'To Date',
        fieldtype: 'Date',
        default: today,
        change: () => reload_items()
    });

    filters.company = page.add_field({
        label: 'Company',
        fieldtype: 'Link',
        options: 'Company',
        default: frappe.defaults.get_default("Company"),
        change: () => reload_items()
    });

    // ✅ NEW COST CENTER FILTER
    filters.cost_center = page.add_field({
        label: 'Cost Center',
        fieldtype: 'Link',
        options: 'Cost Center',
        reqd: 0,
        change: () => reload_items()
    });

    filters.period = page.add_field({
        label: 'Period',
        fieldtype: 'Select',
        options: ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'],
        default: 'Monthly',
        change: () => reload_items()
    });

    // 🔹 Chart + Table Containers
    $(`
        <div class="p-4 space-y-4">
            <div id="chart-area" style="height:350px;"></div>
            <div id="data-table" class="mt-4"></div>
        </div>
    `).appendTo(page.body);

    // 🔹 Load Function
    function reload_items() {
        const f = {
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value(),
            company: filters.company.get_value(),
            cost_center: filters.cost_center.get_value(),
            period: filters.period.get_value()
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.revenue_vs_target.get_revenue_vs_target",
            args: { filters: f },
            freeze: true,
            freeze_message: __("Fetching Revenue vs Target..."),
            callback: function (r) {
                if (!r.message || !r.message.length) {
                    $('#chart-area').html("<p class='text-muted text-center mt-4'>No data found for the selected filters.</p>");
                    $('#data-table').empty();
                    return;
                }

                const data = r.message;
                const labels = data.map(d => d.period_label);
                const revenue = data.map(d => d.revenue);
                const target = data.map(d => d.target);
                const sply = data.map(d => d.sply);

                new frappe.Chart("#chart-area", {
                    title: "Revenue vs Target",
                    data: {
                        labels: labels,
                        datasets: [
                            { name: "Revenue", values: revenue },
                            { name: "Target", values: target },
                            { name: "SPLY", values: sply }
                        ]
                    },
                    type: 'bar',
                    height: 300,
                    colors: ['#2490ef', '#f0ad4e', '#34d399']
                });

                let html = `
                    <table class="table table-bordered table-sm">
                        <thead>
                            <tr>
                                <th>Period</th>
                                <th>Outlet</th>
                                <th>Cost Center</th>
                                <th>Revenue</th>
                                <th>Target</th>
                                <th>Variance</th>
                                <th>Achievement %</th>
                                <th>SPLY</th>
                                <th>Growth %</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.map(d => `
                                <tr>
                                    <td>${d.period_label}</td>
                                    <td>${d.outlet || '-'}</td>
                                    <td>${d.cost_center || '-'}</td>
                                    <td>${format_currency(d.revenue)}</td>
                                    <td>${format_currency(d.target)}</td>
                                    <td>${format_currency(d.revenue - d.target)}</td>
                                    <td>${(d.achievement || 0).toFixed(1)}%</td>
                                    <td>${format_currency(d.sply)}</td>
                                    <td>${(d.growth || 0).toFixed(1)}%</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>`;
                $('#data-table').html(html);
            }
        });
    }

    // Initial Load
    reload_items();
};
