frappe.pages['item-wise-sales-hist'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Item-wise Sales History',
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
    filters.sales_invoice = page.add_field({ label: 'Sales Invoice', fieldtype: 'Link', options: 'Sales Invoice', change: () => reload_items() });

    // --- Buttons ---
    const $buttons = $(`
        <div class="mb-2 text-right">
            <button class="btn btn-secondary" id="export-excel">Export to Excel</button>
            <button class="btn btn-secondary" id="print-pdf">Print PDF</button>
            <button class="btn btn-primary" id="calculate-totals">Calculate Totals</button>
        </div>
    `).appendTo(page.body);

    // --- Table Container ---
    const $container = $(`
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" id="item-wise-table">
                <thead class="thead-dark">
                    <tr>
                        <th>Sales Invoice</th>
                        <th>Item Code</th>
                        <th>Item Group</th>
                        <th>Qty</th>
                        <th>Rate</th>
                        <th>Amount</th>
                        <th>Warehouse</th>
                        <th>Cost Center</th>
                        <th>Date</th>
                        <th>Customer</th>
                    </tr>
                </thead>
                <tbody id="item-wise-body"></tbody>
            </table>
        </div>
        <div class="mt-3 text-center">
            <button class="btn btn-outline-primary" id="load-more-btn">Load More</button>
        </div>
    `).appendTo(page.body);

    // --- Totals Display ---
    const $totals = $(`
        <div class="mt-2 text-right">
            <strong>Total Qty: </strong><span id="total-qty">0</span> &nbsp;&nbsp;
            <strong>Total Amount: </strong><span id="total-amount">0.00</span>
        </div>
    `).appendTo(page.body);

    // --- State ---
    let start = 0, page_length = 50, loading = false;
    const $tbody = $('#item-wise-body');
    const $loadBtn = $('#load-more-btn');
    const $table = $('#item-wise-table');

    // --- Load Items ---
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
           method: "gormsolutions_mobile_app.custom_api.reports.item_sold.get_item_wise_sales_history",
            args:{
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                warehouse: filters.warehouse.get_value(),
                item: filters.item.get_value(),
                item_group: filters.item_group.get_value(),
                cost_center: filters.cost_center.get_value(),
                customer: filters.customer.get_value(),
                sales_invoice: filters.sales_invoice.get_value(),
                start: start,
                page_length: page_length
            },
            callback: function(r){
                console.log(r);
                if(r.message && r.message.length > 0){
                    const rows = r.message.map(row => `
                        <tr>
                            <td><a href="/app/sales-invoice/${row.sales_invoice}" target="_blank">${row.sales_invoice || ''}</a></td>
                            <td>${row.item_code || ''}</td>
                            <td>${row.item_group || ''}</td>
                            <td class="text-right">${row.qty ? parseFloat(row.qty).toLocaleString() : 0}</td>
                            <td class="text-right">${row.rate ? parseFloat(row.rate).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}) : 0}</td>
                            <td class="text-right">${row.amount ? parseFloat(row.amount).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}) : 0}</td>
                            <td>${row.warehouse || ''}</td>
                            <td>${row.cost_center || ''}</td>
                            <td>${row.posting_date || ''}</td>
                            <td>${row.customer || ''}</td>
                        </tr>
                    `).join('');
                    $tbody.append(rows);
                    start += page_length;
                    $loadBtn.text('Load More');
                } else {
                    $loadBtn.text('No More Records').prop('disabled', true);
                }
                loading = false;
            }
        });
    }

    function reload_items(){ load_items(true); }
    $loadBtn.on('click', () => load_items());

    // --- Excel Export ---
    $('#export-excel').on('click', function() {
        function export_excel() {
            let wb = XLSX.utils.book_new();
            let ws = XLSX.utils.table_to_sheet($table[0]);
            XLSX.utils.book_append_sheet(wb, ws, "Item-wise Sales History");
            XLSX.writeFile(wb, `ItemWiseSalesHistory_${frappe.datetime.get_today()}.xlsx`);
        }

        if(typeof XLSX === "undefined") {
            let script = document.createElement('script');
            script.src = "https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js";
            script.onload = export_excel;
            document.head.appendChild(script);
        } else {
            export_excel();
        }
    });

    // --- Print PDF ---
    $('#print-pdf').on('click', function(){
        let printWindow = window.open('', '', 'height=800,width=1200');
        printWindow.document.write('<html><head><title>Item-wise Sales History</title>');
        printWindow.document.write('<link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">');
        printWindow.document.write('<style>table{width:100%;border-collapse:collapse;}table,th,td{border:1px solid #000;}th,td{padding:5px;text-align:right;}th{text-align:center;background-color:#f2f2f2;}</style>');
        printWindow.document.write('</head><body>');
        printWindow.document.write($table.prop('outerHTML'));
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        setTimeout(()=>{ printWindow.print(); }, 500);
    });

    // --- Calculate Totals ---
    $('#calculate-totals').on('click', function(){
        let total_qty = 0;
        let total_amount = 0;

        $('#item-wise-body tr').each(function(){
            total_qty += parseFloat($(this).find('td').eq(3).text().replace(/,/g,'')) || 0;
            total_amount += parseFloat($(this).find('td').eq(5).text().replace(/,/g,'')) || 0;
        });

        $('#total-qty').text(total_qty.toLocaleString());
        $('#total-amount').text(total_amount.toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}));
    });

    // --- Initial Load ---
    load_items(true);
};
