frappe.pages['cash-flow-analysis'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Cash Flow Analysis (Inflow vs Outflow)',
        single_column: true
    });

    // 🔹 Filters
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

    filters.cost_center = page.add_field({
        label: 'Cost Center',
        fieldtype: 'Link',
        options: 'Cost Center',
        change: () => reload_items()
    });

    filters.account = page.add_field({
        label: 'Account',
        fieldtype: 'Link',
        options: 'Account',
        change: () => reload_items()
    });

    filters.period = page.add_field({
        label: 'Period',
        fieldtype: 'Select',
        options: ['Daily','Weekly','Monthly','Quarterly','Yearly'],
        default: 'Monthly',
        change: () => reload_items()
    });

    // 🔹 Chart + Table + Actions
    let $container = $(`
        <div class="p-4 space-y-4">
            <div class="btn-group mb-2">
                <button class="btn btn-primary" id="print_btn">Print</button>
                <button class="btn btn-secondary" id="excel_btn">Download Excel</button>
            </div>
            <div id="chart-area" style="height:350px;"></div>
            <div id="data-table" class="mt-4"></div>
        </div>
    `).appendTo(page.body);

    // 🔹 Reload function
    function reload_items() {
        const f = {
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value(),
            company: filters.company.get_value(),
            cost_center: filters.cost_center.get_value(),
            account: filters.account.get_value(),
            period: filters.period.get_value()
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.cash_flow.get_cash_flow_analysis",
            args: { filters: f },
            freeze: true,
            freeze_message: __("Fetching Cash Flow..."),
            callback: function(r) {
                if(!r.message || !r.message.length){
                    $('#chart-area').html("<p class='text-muted text-center mt-4'>No data found for selected filters.</p>");
                    $('#data-table').empty();
                    return;
                }

                const data = r.message;
                const labels = data.map(d => d.period_label);
                const inflow = data.map(d => d.inflow);
                const outflow = data.map(d => d.outflow);
                const net = data.map(d => d.net_cash_flow);

                // 🔹 Chart
                new frappe.Chart("#chart-area", {
                    title: "Cash Flow (Inflow vs Outflow)",
                    data: {
                        labels: labels,
                        datasets: [
                            { name: "Inflow", values: inflow },
                            { name: "Outflow", values: outflow },
                            { name: "Net", values: net }
                        ]
                    },
                    type: 'bar',
                    height: 300,
                    colors: ['#34d399','#f87171','#60a5fa']
                });

                // 🔹 Table
                let html = `<table class="table table-bordered table-sm">
                    <thead>
                        <tr>
                            <th>Period</th>
                            <th>Inflow</th>
                            <th>Outflow</th>
                            <th>Net Cash Flow</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(d => `
                            <tr>
                                <td>${d.period_label}</td>
                                <td>${format_currency(d.inflow)}</td>
                                <td>${format_currency(d.outflow)}</td>
                                <td>${format_currency(d.net_cash_flow)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>`;
                $('#data-table').html(html);

                // 🔹 Action Buttons
                $('#print_btn').off('click').on('click', () => {
                    frappe.web_print.print_grid($container.find('table')[0]);
                });

                $('#excel_btn').off('click').on('click', () => {
                    frappe.tools.downloadify({
                        data: data.map(d => ({
                            Period: d.period_label,
                            Inflow: d.inflow,
                            Outflow: d.outflow,
                            Net: d.net_cash_flow
                        })),
                        filename: 'Cash_Flow.xlsx'
                    });
                });
            }
        });
    }

    // Initial Load
    reload_items();
};
