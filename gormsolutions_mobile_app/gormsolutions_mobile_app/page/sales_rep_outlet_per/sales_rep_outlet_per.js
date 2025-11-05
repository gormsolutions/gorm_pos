frappe.pages['sales-rep-outlet-per'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales Rep / Cost Center Performance',
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

    let $container = $(`
        <div class="mt-4">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h4>Sales Rep / Cost Center Performance</h4>
                <button class="btn btn-primary btn-sm" id="print-pdf">Print PDF</button>
            </div>
            <div id="sales-performance-table" class="mt-3"></div>
        </div>
    `);
    $(wrapper).find('.layout-main-section').append($container);

    // Print PDF button with professional header
    $container.find('#print-pdf').on('click', function() {
        let tableHtml = document.getElementById('sales-performance-table').innerHTML;
        let company = filters.company.get_value() || "";
        let from_date = filters.from_date.get_value();
        let to_date = filters.to_date.get_value();

        let printContents = `
            <div style="text-align:center; margin-bottom:20px;">
                <h2>${company}</h2>
                <h3>Sales Rep / Cost Center Performance</h3>
                <p><strong>From:</strong> ${from_date} &nbsp;&nbsp; <strong>To:</strong> ${to_date}</p>
                <hr style="margin-top:10px; margin-bottom:20px;">
            </div>
            ${tableHtml}
        `;

        let originalContents = document.body.innerHTML;
        document.body.innerHTML = printContents;

        window.print();

        document.body.innerHTML = originalContents;
        location.reload(); // restore page after printing
    });

    function reload_data() {
        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.sales_rep_outler.get_performance",
            args: {
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                sales_rep: filters.sales_rep.get_value(),
                cost_center: filters.cost_center.get_value(),
                customer: filters.customer.get_value()
            },
            callback: function(r) {
                render_table(r.message || []);
            }
        });
    }

    function render_table(data) {
        let html = `
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Sales Rep</th>
                        <th>Cost Center</th>
                        <th>Customer</th>
                        <th>Total Sales</th>
                        <th>Number of Invoices</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(d => `
                        <tr>
                            <td>${d.sales_rep}</td>
                            <td>${d.cost_center}</td>
                            <td>${d.customer}</td>
                            <td>${format_currency(d.total_sales, "NGN")}</td>
                            <td>${d.invoice_count}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
        $("#sales-performance-table").html(html);
    }

    reload_data();
}
