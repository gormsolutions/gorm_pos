frappe.pages['procurement-spend-tr'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Procurement Spend Trends (YoY, MoM, SPLY)',
        single_column: true
    });

    let filters = {};
    let today = frappe.datetime.get_today();
    let from_default = frappe.datetime.add_months(today, -2); // last 3 months

    // Filters
    filters.from_date = page.add_field({
        label: 'From Date', fieldtype: 'Date',
        default: from_default, reqd: 1, change: reload_data
    });
    filters.to_date = page.add_field({
        label: 'To Date', fieldtype: 'Date',
        default: today, reqd: 1, change: reload_data
    });
    filters.company = page.add_field({
        label: 'Company', fieldtype: 'Link',
        options: 'Company',
        default: frappe.defaults.get_default("Company"), change: reload_data
    });
    filters.supplier = page.add_field({
        label: 'Supplier', fieldtype: 'Link',
        options: 'Supplier', change: reload_data
    });
    filters.item_code = page.add_field({
        label: 'Item', fieldtype: 'Link',
        options: 'Item', change: reload_data
    });
    filters.cost_center = page.add_field({
        label: 'Cost Center', fieldtype: 'Link',
        options: 'Cost Center', change: reload_data
    });

    let $container = $(`
        <div class="mt-4">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h4>Procurement Spend Trends (YoY, MoM, SPLY)</h4>
                <button class="btn btn-primary btn-sm" id="print-pdf">Print PDF</button>
            </div>
            <div id="procurement-trends-table" class="mt-3"></div>
        </div>
    `);
    $(wrapper).find('.layout-main-section').append($container);

    // Print PDF
    $container.find('#print-pdf').on('click', function() {
        let tableHtml = document.getElementById('procurement-trends-table').innerHTML;
        let company = filters.company.get_value() || "";
        let from_date = filters.from_date.get_value();
        let to_date = filters.to_date.get_value();

        let printContents = `
            <div style="text-align:center; margin-bottom:20px;">
                <h2>${company}</h2>
                <h3>Procurement Spend Trends (YoY, MoM, SPLY)</h3>
                <p><strong>From:</strong> ${from_date} &nbsp;&nbsp; <strong>To:</strong> ${to_date}</p>
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

    function reload_data() {
        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.procurement_trends.get_procurement_trends",
            args: {
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                supplier: filters.supplier.get_value(),
                item_code: filters.item_code.get_value(),
                cost_center: filters.cost_center.get_value()
            },
            callback: function(r) {
                render_table(r.message || {});
            }
        });
    }

    function render_table(data) {
        function display(val) {
            return (val === null || val === undefined || val === 0) ? "-" : format_currency(val, "NGN");
        }

        let html = `
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Period</th>
                        <th>Current</th>
                        <th>MoM</th>
                        <th>SPLY</th>
                    </tr>
                </thead>
                <tbody>
                    ${Object.keys(data).map(period => `
                        <tr>
                            <td>${period}</td>
                            <td>${display(data[period].current)}</td>
                            <td>${display(data[period].mom)}</td>
                            <td>${display(data[period].sply)}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
        $("#procurement-trends-table").html(html);
    }

    reload_data();
}
