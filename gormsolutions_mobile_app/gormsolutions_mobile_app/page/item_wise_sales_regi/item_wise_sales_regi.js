frappe.pages['item-wise-sales-regi'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Item-wise Sales Register',
        single_column: true
    });

    // --- Filters ---
    let filters = {};
    let today = frappe.datetime.get_today();

    filters.from_date = page.add_field({ label: 'From Date', fieldtype: 'Date', default: today, change: () => reload_items() });
    filters.to_date = page.add_field({ label: 'To Date', fieldtype: 'Date', default: today, change: () => reload_items() });
    filters.company = page.add_field({ label: 'Company', fieldtype: 'Link', options: 'Company', default: frappe.defaults.get_default("Company"), change: () => reload_items() });
    filters.warehouse = page.add_field({ label: 'Warehouse', fieldtype: 'Link', options: 'Warehouse', change: () => reload_items() });
    filters.item = page.add_field({ label: 'Item', fieldtype: 'Link', options: 'Item', change: () => reload_items() });
    filters.item_group = page.add_field({ label: 'Item Group', fieldtype: 'Link', options: 'Item Group', change: () => reload_items() });
    filters.cost_center = page.add_field({ label: 'Cost Center', fieldtype: 'Link', options: 'Cost Center', change: () => reload_items() });
    filters.customer = page.add_field({ label: 'Customer', fieldtype: 'Link', options: 'Customer', change: () => reload_items() });
    filters.invoice = page.add_field({ label: 'Invoice', fieldtype: 'Link', options: 'Sales Invoice', change: () => reload_items() });

    // --- Totals Display ---
    const $totals = $(`
        <div class="mt-2 mb-2 text-right">
            <strong>Total Qty Sold: </strong><span id="total-qty">0</span> &nbsp;&nbsp;
            <strong>Total Amount: </strong><span id="total-amount">0.00</span>
            <button class="btn btn-primary btn-sm ml-3" id="calculate-totals">Recalculate Totals</button>
        </div>
    `).prependTo(page.body);

    // --- Buttons ---
    const $buttons = $(`
        <div class="mb-2 text-right">
            <button class="btn btn-secondary" id="export-excel">Export to Excel</button>
            <button class="btn btn-secondary" id="print-pdf">Print PDF</button>
        </div>
    `).appendTo(page.body);

    // --- Table Container ---
    const $container = $(`
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" id="flavour-table">
                <thead class="thead-dark">
                    <tr>
                        <th>Posting Date</th>
                        <th>Invoice</th>
                        <th>Customer</th>
                        <th>Item Code</th>
                        <th>Item Group</th>
                        <th>Qty Sold</th>
                        <th>Rate</th>
                        <th>Amount</th>
                    </tr>
                </thead>
                <tbody id="flavour-body"></tbody>
            </table>
        </div>
        <div class="mt-3 text-center">
            <button class="btn btn-outline-primary" id="load-more-btn">Load More</button>
        </div>
    `).appendTo(page.body);

    // --- State ---
    let start = 0, page_length = 50, loading = false;
    const $tbody = $('#flavour-body');
    const $loadBtn = $('#load-more-btn');
    const $table = $('#flavour-table');

    // --- Load Data ---
    function load_items(reset=false){
        if(loading) return;
        if(reset){ 
            $tbody.empty(); 
            start = 0; 
            $loadBtn.prop('disabled', false).text('Load More'); 
        }

        loading = true;
        $loadBtn.text('Loading...');

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.item_wise_sales_register.get_item_wise_sales_register",
            args:{
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                warehouse: filters.warehouse.get_value(),
                item: filters.item.get_value(),
                item_group: filters.item_group.get_value(),
                cost_center: filters.cost_center.get_value(),
                customer: filters.customer.get_value(),
                invoice: filters.invoice.get_value(),
                start: start,
                page_length: page_length
            },
            callback: function(r){
                console.log(r);
                if(r.message && r.message.length > 0){
                    const rows = r.message.map(row => `
                        <tr>
                            <td>${row.posting_date || ''}</td>
                            <td>
                                ${row.invoice ? `<a href="#" onclick="frappe.set_route('Form', 'Sales Invoice', '${row.invoice}'); return false;">${row.invoice}</a>` : ''}
                            </td>
                            <td>${row.customer_name || row.customer || ''}</td>
                            <td>${row.item_code || ''}</td>
                            <td>${row.item_group || ''}</td>
                            <td class="text-right">${row.stock_qty ? parseFloat(row.stock_qty).toLocaleString() : 0}</td>
                            <td class="text-right">${row.rate ? parseFloat(row.rate).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}) : 0}</td>
                            <td class="text-right">${row.amount ? parseFloat(row.amount).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}) : 0}</td>
                        </tr>
                    `).join('');
                    $tbody.append(rows);
                    start += page_length;
                    $loadBtn.text('Load More');

                    // Auto update totals
                    calculate_totals();
                } else {
                    $loadBtn.text('No More Records').prop('disabled', true);
                }
                loading = false;
            }
        });
    }

    function reload_items(){ load_items(true); }
    $loadBtn.on('click', load_items);

    // --- Totals Calculation ---
    function calculate_totals(){
        let total_qty = 0;
        let total_amount = 0;

        $('#flavour-body tr').each(function(){
            total_qty += parseFloat($(this).find('td').eq(5).text().replace(/,/g,'')) || 0;
            total_amount += parseFloat($(this).find('td').eq(7).text().replace(/,/g,'')) || 0;
        });

        $('#total-qty').text(total_qty.toLocaleString());
        $('#total-amount').text(total_amount.toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}));
    }

    $('#calculate-totals').on('click', calculate_totals);

    // --- Excel Export ---
    frappe.require('https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js', function(){
        $('#export-excel').on('click', function(){
            if(typeof XLSX === "undefined"){ frappe.msgprint("Excel library not loaded!"); return; }
            let wb = XLSX.utils.book_new();
            let ws = XLSX.utils.table_to_sheet($table[0]);
            XLSX.utils.book_append_sheet(wb, ws, "Flavour-wise Sales");
            XLSX.writeFile(wb, `FlavourWiseSales_${frappe.datetime.get_today()}.xlsx`);
        });
    });

    // --- Print PDF ---
    $('#print-pdf').on('click', function(){
        let printWindow = window.open('', '', 'height=800,width=1200');
        printWindow.document.write('<html><head><title>Flavour-wise Sales</title>');
        printWindow.document.write('<link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">');
        printWindow.document.write('</head><body>');
        printWindow.document.write($table.prop('outerHTML'));
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        printWindow.print();
    });

    // --- Initial Load ---
    load_items(true);
};
