frappe.pages['revenue-and-expense'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Revenue and Expense Comparison (SPLY)',
        single_column: true
    });

    // Filters
    let filters = {};
    let today = frappe.datetime.get_today();

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

    let $container = $(`
        <div class="mt-4">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <button class="btn btn-primary btn-sm" id="print-pdf">Print PDF</button>
            </div>
            <div id="revenue-expense-table" class="mt-3"></div>
        </div>
    `);
    $(wrapper).find('.layout-main-section').append($container);

    // Print PDF button
    $container.find('#print-pdf').on('click', function() {
        let tableHtml = document.getElementById('revenue-expense-table').innerHTML;
        let company = filters.company.get_value() || "";
        let from_date = filters.from_date.get_value();
        let to_date = filters.to_date.get_value();

        let printContents = `
            <div style="text-align:center; margin-bottom:20px;">
                <h2>${company}</h2>
                <p><strong>From:</strong> ${from_date} &nbsp;&nbsp; <strong>To:</strong> ${to_date}</p>
                <hr style="margin-top:10px; margin-bottom:20px;">
            </div>
            ${tableHtml}
        `;

        let originalContents = document.body.innerHTML;
        document.body.innerHTML = printContents;

        window.print();

        document.body.innerHTML = originalContents;
        location.reload(); // restore page
    });

    function reload_data() {
        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.revenue_expense_comparison.get_revenue_expense_comparison",
            args: {
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                cost_center: filters.cost_center.get_value()
            },
            callback: function(r) {
                render_table(r.message || {});
            }
        });
    }

    function render_table(data) {
    function display(val) {
        return (val === null || val === undefined) ? "-" : format_currency(val, "NGN");
    }


        let html = `
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Current Period</th>
                        <th>Same Period Last Year (SPLY)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Revenue</td>
                        <td>${display(data.revenue)}</td>
                        <td>${display(data.revenue_sply)}</td>
                    </tr>
                    <tr>
                        <td>Expenses</td>
                        <td>${display(data.expenses)}</td>
                        <td>${display(data.expenses_sply)}</td>
                    </tr>
                </tbody>
            </table>
        `;
        $("#revenue-expense-table").html(html);
    }

    reload_data();
}
