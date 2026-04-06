frappe.pages['daily-sales-funds'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Daily Sales Funds',
        single_column: true
    });

    // --- Filters ---
    let filters = {};
    let today = frappe.datetime.get_today();

    filters.from_date = page.add_field({
        label: 'From Date', fieldtype: 'Date',
        default: today,
        change: debounce_reload
    });

    filters.to_date = page.add_field({
        label: 'To Date', fieldtype: 'Date',
        default: today,
        change: debounce_reload
    });

    filters.cost_center = page.add_field({
        label: 'Cost Center', fieldtype: 'Link',
        options: 'Cost Center',
        change: debounce_reload
    });

    filters.account = page.add_field({
        label: 'Account', fieldtype: 'Link',
        options: 'Account',
        change: debounce_reload
    });

    // ✅ Fetch permitted companies dynamically
    frappe.call({
        method: "gormsolutions_mobile_app.custom_api.restrictions.permisions.get_user_companies",
    }).then(r => {
        const companies = r.message || [];

        if (!companies.length) {
            filters.company = page.add_field({
                label: 'Company',
                fieldtype: 'Select',
                options: ['No Permitted Company'],
                default: 'No Permitted Company',
                read_only: 1
            });
            return;
        }

        const options = companies.join('\n');
        const default_company = companies.length === 1 ? companies[0] : (frappe.defaults.get_default("Company") || companies[0]);

        filters.company = page.add_field({
            label: 'Company',
            fieldtype: 'Select',
            options: options,
            default: default_company,
            reqd: 1,
            change: debounce_reload
        });

        filters.company.set_value(default_company);

        // ✅ Load initial data for the default company
        load_data(false);
    });

    // --- Buttons & Table setup ---
    const $controls = $(`
        <div class="mb-3 d-flex justify-content-between align-items-center flex-wrap" style="gap:10px;">
            <div class="d-flex align-items-center gap-2">
                <label class="mb-0">Rows per load:
                    <select id="page-size" class="form-select form-select-sm ms-1">
                        <option value="50" selected>50</option>
                        <option value="100">100</option>
                        <option value="200">200</option>
                        <option value="500">500</option>
                        <option value="1000">1000</option>
                    </select>
                </label>
                <button class="btn btn-primary btn-sm" id="load-more">Load More</button>
                <span id="loading-indicator" style="display:none;">Loading...</span>
            </div>
            <div class="d-flex gap-2">
                <button class="btn btn-secondary btn-sm" id="export-excel">Export to Excel</button>
                <button class="btn btn-secondary btn-sm" id="print-pdf">Print PDF</button>
            </div>
        </div>
    `).appendTo(page.body);

    const $tableContainer = $(`
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" id="daily-sales-funds-table">
                <thead class="thead-dark sticky-top">
                    <tr>
                        <th>#</th>
                        <th>Account</th>
                        <th class="text-end">Inflows</th>
                    </tr>
                </thead>
                <tbody id="daily-sales-funds-body"></tbody>
                <tfoot class="table-light">
                    <tr>
                        <th colspan="2" class="text-end">Total Inflows</th>
                        <th class="text-end" id="total-inflows">0.00</th>
                    </tr>
                </tfoot>
            </table>
        </div>
    `).appendTo(page.body);

    const $tbody = $('#daily-sales-funds-body');
    let current_start = 0;
    let page_size = parseInt($('#page-size').val());

    // --- Load Data ---
    function load_data(load_more = false) {
        if (!filters.company || !filters.company.get_value()) return;

        if (!load_more) {
            current_start = 0; 
            $tbody.empty();
            $('#total-inflows').text('0.00');
        }

        $('#load-more').prop('disabled', true); 
        $('#loading-indicator').show();

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.daily_sales_funds_report.get_daily_sales_funds",
            args: {
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                cost_center: filters.cost_center.get_value(),
                account: filters.account.get_value(),
                limit_start: current_start,
                limit_page_length: page_size
            },
            callback: function(r) {
                $('#load-more').prop('disabled', false);
                $('#loading-indicator').hide();

                if (r.message && r.message.length) {
                    let rows = '';
                    let running_total = parseFloat($('#total-inflows').text().replace(/,/g, '')) || 0;

                    r.message.forEach((row, idx) => {
                        rows += `<tr>
                            <td>${current_start + idx + 1}</td>
                            <td>${row.account || ''}</td>
                            <td class="text-end">${row.inflows ? 
                                parseFloat(row.inflows).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) 
                                : '0.00'}</td>
                        </tr>`;
                        running_total += parseFloat(row.inflows) || 0;
                    });

                    $tbody.append(rows);
                    $('#total-inflows').text(running_total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                    current_start += r.message.length;
                }
            }
        });
    }

    // --- Debounce reload ---
    let debounce_timer;
    function debounce_reload() {
        clearTimeout(debounce_timer);
        debounce_timer = setTimeout(() => load_data(false), 400);
    }

    // --- Button Events ---
    $('#load-more').on('click', () => load_data(true));
    $('#page-size').on('change', function () {
        page_size = parseInt($(this).val());
        load_data(false);
    });

    $('#export-excel').on('click', function () {
        function export_excel() {
            let wb = XLSX.utils.book_new();
            let ws = XLSX.utils.table_to_sheet($('#daily-sales-funds-table')[0]);
            XLSX.utils.book_append_sheet(wb, ws, "Daily Sales Funds");
            XLSX.writeFile(wb, `DailySalesFunds_${frappe.datetime.get_today()}.xlsx`);
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

    $('#print-pdf').on('click', function () {
        let printWindow = window.open('', '', 'height=800,width=1200');
        printWindow.document.write('<html><head><title>Daily Sales Funds</title>');
        printWindow.document.write('<link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">');
        printWindow.document.write('</head><body>');
        printWindow.document.write($('#daily-sales-funds-table').prop('outerHTML'));
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        setTimeout(() => { printWindow.print(); }, 500);
    });
};
