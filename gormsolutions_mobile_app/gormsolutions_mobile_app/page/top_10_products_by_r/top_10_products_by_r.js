frappe.pages['top-10-products-by-r'].on_page_load = function(wrapper) {

    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Top 10 Products by Revenue',
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

    filters.item_code = page.add_field({
        label: 'Item', fieldtype: 'Link',
        options: 'Item',
        change: reload_data
    });

    let $container = $(`
        <div class="mt-4">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h4>Top 10 Products by Revenue</h4>
                <button class="btn btn-primary btn-sm" id="print-pdf">Print PDF</button>
            </div>
            <div id="top-products-table" class="mt-3"></div>
        </div>
    `);
    $(wrapper).find('.layout-main-section').append($container);

    // Print PDF button with professional header
    $container.find('#print-pdf').on('click', function() {
        let tableHtml = document.getElementById('top-products-table').innerHTML;
        let company = filters.company.get_value() || "";
        let from_date = filters.from_date.get_value();
        let to_date = filters.to_date.get_value();

        let printContents = `
            <div style="text-align:center; margin-bottom:20px;">
                <h2>${company}</h2>
                <h3>Top 10 Products by Revenue</h3>
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
            method: "gormsolutions_mobile_app.custom_api.reports.top_10_products.get_top_products",
            args: {
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                cost_center: filters.cost_center.get_value(),
                item_code: filters.item_code.get_value()
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
                        <th>Item</th>
                        <th>Item Name</th>
                        <th>Total Revenue</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(d => `
                        <tr>
                            <td>${d.item_code}</td>
                            <td>${d.item_name}</td>
                            <td>${format_currency(d.total_revenue, "NGN")}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
        $("#top-products-table").html(html);
    }

    reload_data();
}
