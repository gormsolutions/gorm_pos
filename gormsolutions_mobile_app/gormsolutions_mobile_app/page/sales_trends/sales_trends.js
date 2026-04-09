frappe.pages['sales-trends'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales Trends Comparison',
        single_column: true
    });

    let filters = {};
    let today = frappe.datetime.get_today();

    // Period 1
    filters.from_date1 = page.add_field({
        label: 'From Date (Period 1)', fieldtype: 'Date',
        default: today, reqd: 1, change: reload_data
    });
    filters.to_date1 = page.add_field({
        label: 'To Date (Period 1)', fieldtype: 'Date',
        default: today, reqd: 1, change: reload_data
    });

    // Period 2
    filters.from_date2 = page.add_field({
        label: 'From Date (Period 2)', fieldtype: 'Date',
        default: today, reqd: 1, change: reload_data
    });
    filters.to_date2 = page.add_field({
        label: 'To Date (Period 2)', fieldtype: 'Date',
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
                <h4>Sales Trends Comparison</h4>
                <button class="btn btn-primary btn-sm" id="print-pdf">Print PDF</button>
            </div>
            <div id="sales-trends-table" class="mt-3"></div>
        </div>
    `);

    $(wrapper).find('.layout-main-section').append($container);

    // Print PDF
    $container.find('#print-pdf').on('click', function() {
        let tableHtml = document.getElementById('sales-trends-table').innerHTML;
        let company = filters.company.get_value() || "";
        let cost_center = filters.cost_center.get_value() || "";
        let from_date1 = filters.from_date1.get_value();
        let to_date1 = filters.to_date1.get_value();
        let from_date2 = filters.from_date2.get_value();
        let to_date2 = filters.to_date2.get_value();

        let printContents = `
            <div style="text-align:center; margin-bottom:20px;">
                <h2>${company}</h2>
                <h3>Sales Trends Comparison</h3>
                <p>
                    <strong>Cost Center:</strong> ${cost_center || "All"}<br>
                    <strong>Period 1:</strong> ${from_date1} → ${to_date1}<br>
                    <strong>Period 2:</strong> ${from_date2} → ${to_date2}
                </p>
                <hr style="margin-top:10px; margin-bottom:20px;">
            </div>
            ${tableHtml}
        `;

        let originalContents = document.body.innerHTML;
        document.body.innerHTML = printContents;
        window.print();
        document.body.innerHTML = originalContents;
        location.reload();
    });

    // Fetch and render data
    function reload_data() {
        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.get_sales_trends.get_sales_trends",
            args: {
                from_date1: filters.from_date1.get_value(),
                to_date1: filters.to_date1.get_value(),
                from_date2: filters.from_date2.get_value(),
                to_date2: filters.to_date2.get_value(),
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
                        <th>Metric / Period</th>
                        <th>Current Month/Year</th>
                        <th>Last Month/Year</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Total Sales</td>
                        <td>${display(data.period1?.total)}</td>
                        <td>${display(data.period2?.total)}</td>
                    </tr>
                </tbody>
            </table>
        `;
        $("#sales-trends-table").html(html);
    }

    reload_data();
}
