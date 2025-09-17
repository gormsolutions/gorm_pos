frappe.pages['flavour-wise-sales'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales by FLAVOUR and Outlet',
        single_column: true
    });

    // --- Filters ---
    let filters = {}; // must declare first
    let today = frappe.datetime.get_today();

    filters.from_date = page.add_field({
        label: 'From Date', fieldtype: 'Date',
        default: today, change: reload_items
    });
    filters.to_date = page.add_field({
        label: 'To Date', fieldtype: 'Date',
        default: today, change: reload_items
    });
    filters.company = page.add_field({
        label: 'Company', fieldtype: 'Link',
        options: 'Company',
        default: frappe.defaults.get_default("Company"),
        change: reload_items
    });
    filters.warehouse = page.add_field({
        label: 'Warehouse', fieldtype: 'Link',
        options: 'Warehouse', change: reload_items
    });
    filters.invoice = page.add_field({
        label: 'Invoice', fieldtype: 'Link',
        options: 'Sales Invoice', change: reload_items
    });

    filters.flavour = page.add_field({
        label: 'Flavour',
        fieldtype: 'Select',
        options: [],
        change: reload_items
    });

    // Populate flavour options dynamically
    frappe.call({
        method: "gormsolutions_mobile_app.custom_api.reports.item_flavour_sales.get_flavour_values",
        callback: function(r) {
            if (r.message) {
                let flavour_field = filters.flavour.$input;
                flavour_field.empty();
                flavour_field.append(`<option value=""></option>`); // all flavours
                r.message.forEach(d => {
                    flavour_field.append(`<option value="${d.attribute_value}">${d.attribute_value}</option>`);
                });
            }
        }
    });

    filters.item_group = page.add_field({
        label: 'Item Group', fieldtype: 'Link',
        options: 'Item Group', change: reload_items
    });
    filters.cost_center = page.add_field({
        label: 'Cost Center', fieldtype: 'Link',
        options: 'Cost Center', change: reload_items
    });
    filters.customer = page.add_field({
        label: 'Customer', fieldtype: 'Link',
        options: 'Customer', change: reload_items
    });

    // --- Totals & Buttons ---
    const $controls = $(`
        <div class="mt-3 mb-3 d-flex justify-content-between align-items-center">
            <div>
                <strong>Total Qty Sold: </strong><span id="total-qty">0</span> &nbsp;&nbsp;
                <strong>Total Amount: </strong><span id="total-amount">0.00</span>
            </div>
            <div>
                <button class="btn btn-sm btn-success" id="export-excel">Export Excel</button>
                <button class="btn btn-sm btn-secondary" id="print-pdf">Print PDF</button>
                <button class="btn btn-sm btn-primary" id="calculate-totals">Recalculate Totals</button>
            </div>
        </div>
    `).appendTo(page.body);

    // --- Table Container ---
    const $table = $(`
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" id="flavour-table">
                <thead class="thead-dark">
                    <tr>
                        <th>Flavour</th>
                        <th>Invoice</th>
                        <th>Qty Sold</th>
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

    let start = 0, page_length = 50, loading = false;
    const $tbody = $('#flavour-body');
    const $loadBtn = $('#load-more-btn');

    // --- Load Data ---
    function load_items(reset=false){
        if (loading) return;
        if (reset) {
            $tbody.empty();
            start = 0;
            $loadBtn.prop('disabled', false).text('Load More');
        }

        loading = true;
        $loadBtn.text('Loading...');

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.item_flavour_sales.get_flavour_wise_sales",
            args: {
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                warehouse: filters.warehouse.get_value(),
                flavour: filters.flavour.get_value(),
                item_group: filters.item_group.get_value(),
                cost_center: filters.cost_center.get_value(),
                customer: filters.customer.get_value(),
                invoice: filters.invoice.get_value(),
                start: start,
                page_length: page_length
            },
            callback: function(r){
                if (r.message && r.message.length > 0) {
                    const rows = r.message.map(row => `
                        <tr>
                            <td>${row.flavour || ''}</td>
                            <td>
                                ${row.invoice 
                                    ? `<a href="/app/sales-invoice/${row.invoice}" target="_blank">${row.invoice}</a>` 
                                    : ''}
                            </td>
                            <td class="text-right">${row.qty_sold ? parseFloat(row.qty_sold).toLocaleString() : 0}</td>
                            <td class="text-right">${row.amount ? parseFloat(row.amount).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}) : 0}</td>
                        </tr>
                    `).join('');
                    $tbody.append(rows);
                    start += page_length;
                    $loadBtn.text('Load More');
                    calculate_totals();
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
            let ws = XLSX.utils.table_to_sheet(document.getElementById("flavour-table"));
            XLSX.utils.book_append_sheet(wb, ws, "Flavour-wise Sales");
            XLSX.writeFile(wb, `FlavourWiseSales_${frappe.datetime.get_today()}.xlsx`);
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
    $('#print-pdf').on('click', function(){
        let printWindow = window.open('', '', 'height=800,width=1200');
        printWindow.document.write('<html><head><title>Flavour-wise Sales</title>');
        printWindow.document.write('<link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">');
        printWindow.document.write(`
            <style>
                table { width:100%; border-collapse:collapse; }
                table, th, td { border:1px solid #000; }
                th, td { padding:5px; }
                th { text-align:center; background-color:#f2f2f2; }
                td:first-child { text-align:left; }   
                td:nth-child(2), td:nth-child(3), td:nth-child(4) { text-align:right; } 
            </style>
        `);
        printWindow.document.write('</head><body>');
        printWindow.document.write($table.prop('outerHTML'));
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        setTimeout(()=>{ printWindow.print(); }, 500);
    });

    // --- Calculate Totals ---
    function calculate_totals(){
        let total_qty = 0;
        let total_amount = 0;

        $('#flavour-body tr').each(function(){
            total_qty += parseFloat($(this).find('td').eq(2).text().replace(/,/g,'')) || 0;
            total_amount += parseFloat($(this).find('td').eq(3).text().replace(/,/g,'')) || 0;
        });

        $('#total-qty').text(total_qty.toLocaleString());
        $('#total-amount').text(total_amount.toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}));
    }

    $('#calculate-totals').on('click', calculate_totals);

    // --- Initial Load ---
    load_items(true);
};
