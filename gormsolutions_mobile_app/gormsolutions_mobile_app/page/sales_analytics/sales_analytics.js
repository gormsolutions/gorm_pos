frappe.pages['sales-analytics'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales Analytics',
        single_column: true
    });

    // --- Filters ---
    let filters = {};
    let today = frappe.datetime.get_today();

    filters.from_date = page.add_field({ 
        label: 'From Date', fieldtype: 'Date', 
        default: frappe.datetime.add_months(today, -1), 
        change: reload_data 
    });

    filters.to_date = page.add_field({ 
        label: 'To Date', fieldtype: 'Date', 
        default: today, 
        change: reload_data 
    });

    filters.company = page.add_field({ 
        label: 'Company', fieldtype: 'Link', 
        options: 'Company', 
        default: frappe.defaults.get_default("Company"), 
        change: reload_data 
    });

    filters.customer = page.add_field({ 
        label: 'Customer', fieldtype: 'Link', 
        options: 'Customer', 
        change: reload_data 
    });

    // --- Buttons at the top ---
    const $buttons = $(`
        <div class="mb-2 d-flex align-items-center justify-content-between">
            <div>
                <label>Rows per load: 
                    <select id="page-size">
                        <option value="50" selected>50</option>
                        <option value="100">100</option>
                        <option value="200">200</option>
                        <option value="500">500</option>
                        <option value="1000">1000</option>
                    </select>
                </label>
                <button class="btn btn-secondary" id="load-more">Load More</button>
                <span id="loading-indicator" style="display:none; margin-left:10px;">Loading...</span>
            </div>
            <div>
                <button class="btn btn-primary" id="calculate-totals">Calculate Totals</button>
                <button class="btn btn-secondary" id="export-excel">Export to Excel</button>
                <button class="btn btn-secondary" id="print-pdf">Print PDF</button>
            </div>
        </div>
    `).appendTo(page.body);

    // --- Table ---
    const $tableContainer = $(`
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" id="sales-analytics-table">
                <thead class="thead-dark">
                    <tr>
                        <th>Customer</th>
                        <th>Customer Name</th>
                        <th>Month(s)</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody id="sales-analytics-body"></tbody>
            </table>
        </div>
    `).appendTo(page.body);

    const $tbody = $('#sales-analytics-body');

    // --- Pagination variables ---
    let current_start = 0;
    let page_size = parseInt($('#page-size').val());

    // --- Load Data ---
    function load_data(load_more=false) {
        if (!load_more) {
            current_start = 0;
            $tbody.empty();
        }

        $('#load-more').prop('disabled', true);
        $('#loading-indicator').show();

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.sales_analytics.get_sales_analytics",
            args: {
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                customer: filters.customer.get_value(),
                limit_start: current_start,
                limit_page_length: page_size
            },
            callback: function(r) {
                $('#load-more').prop('disabled', false);
                $('#loading-indicator').hide();

                if (r.message && r.message.length) {
                    const rows = r.message.map(row => `
                        <tr>
                            <td>${row.customer || ''}</td>
                            <td>${row.customer_name || ''}</td>
                            <td>${Object.keys(row.months).map(m => 
                                `${m}: ${parseFloat(row.months[m]).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2})}`
                            ).join('<br>')}</td>
                            <td class="text-right">${row.total ? parseFloat(row.total).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}) : '0.00'}</td>
                        </tr>
                    `).join('');
                    $tbody.append(rows);
                    current_start += page_size;

                    $('#load-more').show();
                } else {
                    $('#load-more').hide();
                }
            }
        });
    }

    function reload_data() {
        load_data(false);
    }

    // --- Load More Button ---
    $('#load-more').on('click', function() {
        load_data(true);
    });

    // --- Page size change ---
    $('#page-size').on('change', function() {
        page_size = parseInt($(this).val());
        reload_data();
    });

    // --- Export to Excel ---
    $('#export-excel').on('click', function () {
        function export_excel() {
            let wb = XLSX.utils.book_new();
            let ws = XLSX.utils.table_to_sheet($('#sales-analytics-table')[0]);
            XLSX.utils.book_append_sheet(wb, ws, "Sales Analytics");
            XLSX.writeFile(wb, `SalesAnalytics_${frappe.datetime.get_today()}.xlsx`);
        }
        if (typeof XLSX === "undefined") {
            let script = document.createElement('script');
            script.src = "https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js";
            script.onload = export_excel;
            document.head.appendChild(script);
        } else {
            export_excel();
        }
    });

    // --- Print PDF ---
    $('#print-pdf').on('click', function () {
        let printWindow = window.open('', '', 'height=800,width=1200');
        printWindow.document.write('<html><head><title>Sales Analytics</title>');
        printWindow.document.write('<link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">');
        printWindow.document.write('</head><body>');
        printWindow.document.write($('#sales-analytics-table').prop('outerHTML'));
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        setTimeout(() => { printWindow.print(); }, 500);
    });

    // --- Calculate Totals ---
    $('#calculate-totals').on('click', function () {
        let total = 0;
        $tbody.find('tr').each(function () {
            total += parseFloat($(this).find('td').last().text().replace(/,/g, '')) || 0;
        });
        frappe.msgprint(`Total Sales (Loaded Rows): ${total.toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2})}`);
    });

    // --- Initial Load ---
    load_data();
};
