frappe.pages['stock-ledger-report'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Stock Ledger Report'),
        single_column: true
    });

    /* -------------------- filter fields -------------------- */
    const today = frappe.datetime.get_today();
    const filters = {
        company: page.add_field({
            label: __('Company'),
            fieldtype: 'Link',
            options: 'Company',
            default: frappe.defaults.get_default("company"),
            change: () => reset_and_load()
        }),
        item_code: page.add_field({
            label: __('Item Code'),
            fieldtype: 'Link',
            options: 'Item',
            change: () => reset_and_load()
        }),
        item_name: page.add_field({
            label: __('Item Name'),
            fieldtype: 'Data',
            change: () => debounced_search()
        }),
        item_group: page.add_field({
            label: __('Item Group'),
            fieldtype: 'Link',
            options: 'Item Group',
            change: () => reset_and_load()
        }),
        warehouse: page.add_field({
            label: __('Warehouse'),
            fieldtype: 'Link',
            options: 'Warehouse',
            change: () => reset_and_load()
        }),
        from_date: page.add_field({
            label: __('From Date'),
            fieldtype: 'Date',
            default: today,
            change: () => reset_and_load()
        }),
        to_date: page.add_field({
            label: __('To Date'),
            fieldtype: 'Date',
            default: today,
            change: () => reset_and_load()
        })
    };

    /* -------------------- quick search -------------------- */
    const $quickSearch = $(`
        <div class="frappe-control">
            <input type="text" id="quick-search" class="form-control form-control-sm"
                   placeholder="${__('Type to search code / name')}" style="width:220px;">
        </div>`);
    page.page_actions.append($quickSearch);

    /* -------------------- controls bar -------------------- */
    const $controls = $(`
        <div class="mb-2 d-flex align-items-center justify-content-between">
            <div class="d-flex align-items-center">
                <label>${__('Rows/page')}:
                    <select id="page-size" class="form-control form-control-sm d-inline-block w-auto">
                        <option value="50" selected>50</option>
                        <option value="100">100</option>
                        <option value="200">200</option>
                        <option value="500">500</option>
                    </select>
                </label>
                <button class="btn btn-secondary btn-sm ml-2" id="load-more">${__('Load More')}</button>
                <span id="loading-indicator" class="text-muted ml-2" style="display:none;">${__('Loading...')}</span>
                <span id="rows-loaded" class="text-muted ml-3"></span>
            </div>
            <div>
                <button class="btn btn-secondary btn-sm" id="export-excel">${__('Export Excel')}</button>
                <button class="btn btn-secondary btn-sm" id="print-pdf">${__('Print')}</button>
            </div>
        </div>`).appendTo(page.body);

    /* -------------------- table -------------------- */
    const $tableWrap = $(`
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" id="stock-ledger-table">
                <thead class="thead-dark">
                    <tr>
                        <th>${__('Date & Time')}</th>
                        <th>${__('Voucher')}</th>
                        <th>${__('Item Code')}</th>
                        <th>${__('Item Name')}</th>
                        <th>${__('Warehouse')}</th>
                        <th class="text-right">${__('In')}</th>
                        <th class="text-right">${__('Out')}</th>
                        <th class="text-right">${__('Balance')}</th>
                        <th class="text-right">${__('Rate')}</th>
                        <th class="text-right">${__('Value')}</th>
                    </tr>
                </thead>
                <tbody id="stock-ledger-body"></tbody>
            </table>
        </div>`).appendTo(page.body);

    const $tbody      = $('#stock-ledger-body');
    const $loadBtn    = $('#load-more');
    const $loading    = $('#loading-indicator');
    const $rowsLoaded = $('#rows-loaded');

    /* -------------------- state -------------------- */
    let lastKey   = null;
    let pageSize  = 50; // initial small load
    let isLoading = false;
    let canGrow   = true;
    let allRows   = [];
    let filteredRows = [];

    /* -------------------- fetch data -------------------- */
    function fetch(next = false) {
        if (isLoading) return;
        isLoading = true;

        if (!next) {
            lastKey   = null;
            allRows   = [];
            filteredRows = [];
            $tbody.empty();
            canGrow   = true;
            pageSize  = parseInt($('#page-size').val()) || 50;
        }

        $loadBtn.prop('disabled', true);
        $loading.show();

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.get_stock_ledger_ledger.get_stock_ledger_ledger",
            args: {
                items: filters.item_code.get_value() || filters.item_name.get_value(),
                company: filters.company.get_value(),
                warehouse: filters.warehouse.get_value(),
                item_group: filters.item_group.get_value(),
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                last_key: lastKey,
                page_size: pageSize
            },
            callback: r => {
                if (r.message && r.message.data.length) {
                    const chunk = r.message.data.map(row => ({
                        ...row,
                        valuation_amount: flt(row.stock_value)
                    }));
                    allRows.push(...chunk);
                    lastKey = r.message.next_key;

                    if (r.message.data.length < pageSize) canGrow = false;
                    else if (canGrow) pageSize = Math.min(pageSize * 2, 1000); // progressive load

                    applySearch();
                    $rowsLoaded.text(__('Loaded') + ' ' + allRows.length);
                    lastKey ? $loadBtn.show() : $loadBtn.hide();
                } else {
                    canGrow = false; $loadBtn.hide();
                }
            },
            always: () => { isLoading = false; $loadBtn.prop('disabled', false); $loading.hide(); }
        });
    }

    /* -------------------- infinite scroll -------------------- */
    $tableWrap.on('scroll', function () {
        if (canGrow && !isLoading && (this.scrollTop + this.clientHeight >= this.scrollHeight - 50)) fetch(true);
    });

    /* -------------------- search -------------------- */
    const debounced_search = frappe.utils.debounce(applySearch, 300);
    $('#quick-search').on('input', debounced_search);

    function applySearch() {
        const needle = $('#quick-search').val().trim().toLowerCase();
        filteredRows = needle
            ? allRows.filter(r =>
                (r.item_code || '').toLowerCase().includes(needle) ||
                (r.item_name || '').toLowerCase().includes(needle))
            : allRows;
        renderRows(filteredRows);
    }

    /* -------------------- render table -------------------- */
    function renderRows(rows) {
        const rowsHtml = rows.map(r => `
            <tr>
                <td>${frappe.datetime.str_to_user(r.posting_date)} ${r.posting_time}</td>
                <td>
                    <a href="/app/${r.voucher_type.toLowerCase().replace(' ', '-')}/${r.voucher_no}" target="_blank">
                        ${r.voucher_type}<br><small>${r.voucher_no}</small>
                    </a>
                </td>
                <td>${r.item_code}</td>
                <td>${r.item_name}</td>
                <td>${r.warehouse}</td>
                <td class="text-right text-success">${r.in_qty ? formatNumber(r.in_qty) : ''}</td>
                <td class="text-right text-danger">${r.out_qty ? formatNumber(r.out_qty) : ''}</td>
                <td class="text-right">${formatNumber(r.running_balance)}</td>
                <td class="text-right">${formatNumber(r.valuation_rate)}</td>
                <td class="text-right">${formatNumber(r.valuation_amount)}</td>
            </tr>`).join('');
        $tbody.html(rowsHtml);
    }

    /* -------------------- helpers -------------------- */
    function formatNumber(v) {
        return flt(v, 2).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }
    function reset_and_load() { fetch(false); }

    /* -------------------- export / print -------------------- */
    $('#export-excel').on('click', () => {
        if (typeof XLSX === 'undefined') {
            const s = document.createElement('script');
            s.src = 'https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js';
            s.onload = () => downloadExcel();
            document.head.appendChild(s);
        } else downloadExcel();

        function downloadExcel() {
            const ws_data = [
                ['Date-Time', 'Voucher', 'Item Code', 'Item Name', 'Warehouse', 'In', 'Out', 'Balance', 'Rate', 'Value']
            ];
            filteredRows.forEach(r => ws_data.push([
                `${r.posting_date} ${r.posting_time}`,
                r.voucher_type + ' ' + r.voucher_no,
                r.item_code, r.item_name, r.warehouse,
                r.in_qty, r.out_qty, r.running_balance,
                r.valuation_rate, r.valuation_amount
            ]));
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(ws_data), 'StockLedger');
            XLSX.writeFile(wb, `StockLedger_${frappe.datetime.get_today()}.xlsx`);
        }
    });

    $('#print-pdf').on('click', () => {
        const win = window.open('', 'Print', 'width=1200,height=800');
        win.document.write('<html><head><title>Stock Ledger</title>');
        win.document.write('<link rel="stylesheet" href="/assets/frappe/css/bootstrap-4.css">');
        win.document.write(`<style>
            body{margin:20px;font-size:12px}
            .text-success{color:#28a745;font-weight:bold}
            .text-danger {color:#dc3545;font-weight:bold}
            tfoot td{font-weight:bold;background:#f1f1f1}
        </style></head><body>`);
        win.document.write('<h4>Stock Ledger Report - ' + frappe.datetime.get_today() + '</h4>');
        win.document.write(document.getElementById('stock-ledger-table').outerHTML);
        win.document.write('</body></html>');
        win.document.close();
        setTimeout(() => { win.print(); win.close(); }, 250);
    });

    /* -------------------- keyboard shortcuts -------------------- */
    $(document).on('keydown', e => {
        if (e.ctrlKey && e.key === 'e') $('#export-excel').click();
        if (e.ctrlKey && e.key === 'p') $('#print-pdf').click();
    });

    /* -------------------- UI events -------------------- */
    $('#page-size').on('change', reset_and_load);
    $('#load-more').on('click', () => fetch(true));

    /* -------------------- initial fetch -------------------- */
    fetch(false); // fetch only today initially
};
