frappe.pages['budget-vs-actual-exp'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Budget vs Actual Expenses',
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

    filters.cost_center = page.add_field({
        label: 'Cost Center',
        fieldtype: 'Link',
        options: 'Cost Center',
        reqd: 0,
        change: () => reload_items()
    });

    filters.account = page.add_field({
        label: 'Account',
        fieldtype: 'Link',
        options: 'Account',
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

    // 🔹 Chart + Table + Action Buttons Containers
    let container = $(`
        <div class="p-4 space-y-4">
            <div id="chart-area" style="height:350px;"></div>
            <div class="d-flex justify-end mb-2">
                <button id="btn-print" class="btn btn-secondary btn-sm mr-2">Print PDF</button>
                <button id="btn-excel" class="btn btn-secondary btn-sm">Download Excel</button>
            </div>
            <div id="data-table" class="mt-2"></div>
        </div>
    `).appendTo(page.body);

    // 🔹 Print PDF Button
    $(container).on('click', '#btn-print', function() {
        let table_html = $('#data-table').html();
        let w = window.open('', '_blank');
        w.document.write(`<html><head><title>Budget vs Actual Expenses</title></head><body>${table_html}</body></html>`);
        w.document.close();
        w.print();
    });

    // 🔹 Download Excel Button
    $(container).on('click', '#btn-excel', function() {
        let table_html = $('#data-table table')[0].outerHTML;
        let filename = `Budget_vs_Actual_Expenses_${frappe.datetime.now_date()}.xls`;
        let blob = new Blob([table_html], { type: 'application/vnd.ms-excel' });
        let url = URL.createObjectURL(blob);
        let a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    });

    // 🔹 Load Function
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
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.budget_expense.get_budget_vs_actual_expenses",
            args: { filters: f },
            freeze: true,
            freeze_message: __("Fetching Budget vs Actual Expenses..."),
            callback: function (r) {
                if (!r.message || !r.message.length) {
                    $('#chart-area').html("<p class='text-muted text-center mt-4'>No data found for the selected filters.</p>");
                    $('#data-table').empty();
                    return;
                }

                const data = r.message;
                const labels = data.map(d => d.period_label);
                const actual = data.map(d => d.actual_expense);
                const budget = data.map(d => d.budget);
                const sply = data.map(d => d.sply);

                // 🔹 Chart
                new frappe.Chart("#chart-area", {
                    title: "Budget vs Actual Expenses",
                    data: {
                        labels: labels,
                        datasets: [
                            { name: "Actual Expense", values: actual },
                            { name: "Budget", values: budget },
                            { name: "SPLY", values: sply }
                        ]
                    },
                    type: 'bar',
                    height: 300,
                    colors: ['#f05d23', '#2490ef', '#34d399']
                });

                // 🔹 Table
                let html = `
                    <table class="table table-bordered table-sm">
                        <thead>
                            <tr>
                                <th>Period</th>
                                <th>Cost Center</th>
                                <th>Account</th>
                                <th>Actual Expense</th>
                                <th>Budget</th>
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
                                    <td>${d.cost_center || '-'}</td>
                                    <td>${d.account || '-'}</td>
                                    <td>${format_currency(d.actual_expense)}</td>
                                    <td>${format_currency(d.budget)}</td>
                                    <td>${format_currency(d.actual_expense - d.budget)}</td>
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
