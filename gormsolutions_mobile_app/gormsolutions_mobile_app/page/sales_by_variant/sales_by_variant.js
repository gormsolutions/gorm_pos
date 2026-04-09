frappe.pages['sales-by-variant'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales by Variant',
        single_column: true
    });

    // --- Filters ---
    let filters = {};
    let today = frappe.datetime.get_today();

    filters.from_date = page.add_field({ label: 'From Date', fieldtype: 'Date', default: today, change: () => reload_items(true) });
    filters.to_date = page.add_field({ label: 'To Date', fieldtype: 'Date', default: today, change: () => reload_items(true) });
    filters.company = page.add_field({ label: 'Company', fieldtype: 'Link', options: 'Company', default: frappe.defaults.get_default("Company"), change: () => reload_items(true) });
    filters.cost_center = page.add_field({ label: 'Cost Center', fieldtype: 'Link', options: 'Cost Center', change: () => reload_items(true) });
    filters.item = page.add_field({ label: 'Item', fieldtype: 'Link', options: 'Item', change: () => reload_items(true) });

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

    filters.sales_invoice = page.add_field({ label: 'Sales Invoice', fieldtype: 'Link', options: 'Sales Invoice', change: () => reload_items(true) });

    // --- Totals Display (moved to top) ---
    const $totals = $(`
        <div class="mb-2 text-right">
            <strong>Total Qty: </strong><span id="total-qty">0</span> &nbsp;&nbsp;
            <strong>Total Amount: </strong><span id="total-amount">0.00</span>
        </div>
    `).appendTo(page.body);

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
            <table class="table table-bordered table-hover table-sm" id="sales-variant-table">
                <thead class="thead-dark">
                    <tr>
                        <th>Item Code</th>
                        <th>Qty Sold</th>
                        <th>Amount</th>
                        <th>Size</th>
                        <th>Flavour</th>
                        <th>Company</th>
                        <th>Cost Center</th>
                        <th>Sales Invoice</th>
                    </tr>
                </thead>
                <tbody id="sales-variant-body"></tbody>
            </table>
        </div>
        <div class="mt-3 text-center">
            <button class="btn btn-outline-primary" id="load-more-btn">Load More</button>
        </div>
    `).appendTo(page.body);

    // --- State ---
    let start = 0, page_length = 50, loading = false;
    const $tbody = $('#sales-variant-body');
    const $loadBtn = $('#load-more-btn');
    const $table = $('#sales-variant-table');

    // --- Update Totals Function ---
    function update_totals() {
        let total_qty = 0;
        let total_amount = 0;

        $('#sales-variant-body tr').each(function() {
            let qty = parseFloat($(this).find('td').eq(1).text().replace(/,/g, '')) || 0;
            let amount = parseFloat($(this).find('td').eq(2).text().replace(/,/g, '')) || 0;

            total_qty += qty;
            total_amount += amount;
        });

        $('#total-qty').text(total_qty.toLocaleString());
        $('#total-amount').text(total_amount.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}));
    }

    // --- Load Items ---
    function load_items(reset=false) {
        if (loading) return;
        if (reset) { 
            $tbody.empty(); 
            start = 0; 
            $loadBtn.prop('disabled', false).text('Load More'); 
        }

        loading = true;
        $loadBtn.text('Loading...');

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.sales _by_variant.get_sales_report_optimized",
            args: {
                start_date: filters.from_date.get_value(),
                end_date: filters.to_date.get_value(),
                company: filters.company.get_value(),
                cost_center: filters.cost_center.get_value(),
                item_code: filters.item.get_value(),
                flavour: filters.flavour.get_value() || null,
                sales_invoice_no: filters.sales_invoice.get_value(),
                start: start,
                page_length: page_length
            },
            callback: function(r) {
                if(r.message && r.message.length > 0) {
                    const rows = r.message.map(row => {
                        const invoice_link = row.sales_invoice_no 
                            ? `<a href="#" onclick="frappe.set_route('Form','Sales Invoice','${row.sales_invoice_no}')">${row.sales_invoice_no}</a>` 
                            : '';
                        return `
                        <tr>
                            <td>${row.item_code || ''}</td>
                            <td class="text-right">${row.qty_sold ? parseFloat(row.qty_sold).toLocaleString() : 0}</td>
                            <td class="text-right">${row.amount ? parseFloat(row.amount).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}) : 0}</td>
                            <td>${row.size || ''}</td>
                            <td>${row.flavour || ''}</td>
                            <td>${row.company || ''}</td>
                            <td>${row.cost_center || ''}</td>
                            <td>${invoice_link}</td>
                        </tr>
                        `;
                    }).join('');
                    $tbody.append(rows);
                    start += page_length;
                    $loadBtn.text('Load More');
                    update_totals(); // <-- totals update automatically
                } else {
                    $loadBtn.text('No More Records').prop('disabled', true);
                }
                loading = false;
            }
        });
    }

    function reload_items() { load_items(true); }
    $loadBtn.on('click', () => load_items());

    // --- Excel Export ---
    frappe.require('https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js', function() {
        $('#export-excel').on('click', function() {
            if (typeof XLSX === "undefined") { frappe.msgprint("Excel library not loaded!"); return; }
            let wb = XLSX.utils.book_new();
            let ws = XLSX.utils.table_to_sheet($table[0]);
            XLSX.utils.book_append_sheet(wb, ws, "Sales by Variant");
            XLSX.writeFile(wb, `Sales_by_Variant_${frappe.datetime.get_today()}.xlsx`);
        });
    });

    // --- Print PDF ---
    $('#print-pdf').on('click', function() {
        let printWindow = window.open('', '', 'height=800,width=1200');
        printWindow.document.write('<html><head><title>Sales by Variant</title>');
        printWindow.document.write('<link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">');
        printWindow.document.write('</head><body>');
        printWindow.document.write($table.prop('outerHTML'));
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        printWindow.print();
    });

    // --- Calculate Totals Button ---
    $('#calculate-totals').on('click', update_totals);

    // --- Initial Load ---
    load_items(true);
};
