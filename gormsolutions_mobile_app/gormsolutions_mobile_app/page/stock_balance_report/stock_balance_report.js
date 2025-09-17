frappe.pages['stock-balance-report'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Stock Balance Report'),
        single_column: true
    });

    const today = frappe.datetime.get_today();

    /* -------------------- filter fields -------------------- */
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
            change: () => reset_and_load()
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

    /* -------------------- quick-search box -------------------- */
    const $quickSearch = $(`<div class="frappe-control ml-2">
        <input type="text" id="quick-search" class="form-control form-control-sm"
               placeholder="${__('Type to search code / name / warehouse')}" style="width:250px;">
    </div>`);
    page.page_actions.append($quickSearch);

    /* -------------------- controls row -------------------- */
    const $controls = $(`<div class="mb-2 d-flex align-items-center justify-content-between">
        <div class="d-flex align-items-center">
            <label>${__('Rows/load')}:
                <select id="page-size" class="form-control form-control-sm d-inline-block w-auto">
                    <option value="50">50</option>
                    <option value="100" selected>100</option>
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

    /* -------------------- table + totals bar -------------------- */
    const $tableWrap = $(`<div class="table-responsive">
        <table class="table table-bordered table-hover table-sm" id="stock-balance-table">
            <thead class="thead-dark">
                <tr>
                    <th>${__('Item Code')}</th>
                    <th>${__('Item Name')}</th>
                    <th>${__('Item Group')}</th>
                    <th>${__('UOM')}</th>
                    <th>${__('Warehouse')}</th>
                    <th class="text-right">${__('Balance Qty')}</th>
                    <th class="text-right">${__('Valuation Rate')}</th>
                    <th class="text-right">${__('Valuation Amount')}</th>
                </tr>
            </thead>
            <tbody id="stock-balance-body"></tbody>
            <tfoot id="stock-balance-foot" class="font-weight-bold bg-light">
                <tr>
                    <td colspan="5">TOTAL (visible rows)</td>
                    <td id="total-qty" class="text-right">0</td>
                    <td></td>
                    <td id="total-value" class="text-right">0</td>
                </tr>
            </tfoot>
        </table>
    </div>`).appendTo(page.body);

    const $tbody = $('#stock-balance-body');
    const $tfoot = $('#stock-balance-foot');
    const $loadBtn = $('#load-more');
    const $loading = $('#loading-indicator');
    const $rowsLoaded = $('#rows-loaded');

    /* -------------------- state -------------------- */
    let lastKey = null;
    let pageSize = 100;
    let isLoading = false;
    let allRows = [];
    let filteredRows = [];
    let canGrow = true;

    /* -------------------- fetch data -------------------- */
    function fetch(next = false) {
        if (isLoading) return;
        isLoading = true;

        if (!next) {
            lastKey = null;
            allRows = [];
            filteredRows = [];
            $tbody.empty();
            updateTotals();
            canGrow = true;
            pageSize = parseInt($('#page-size').val());
        }

        $loadBtn.prop('disabled', true);
        $loading.show();

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.get_stock_balance_report.get_latest_stock_balances_pro",
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
                        valuation_amount: flt(row.balance_qty) * flt(row.valuation_rate)
                    }));
                    allRows.push(...chunk);
                    lastKey = r.message.next_key;

                    if (r.message.data.length < pageSize) canGrow = false;
                    else if (canGrow) pageSize = Math.min(pageSize * 2, 1000);

                    applySearch();
                    $rowsLoaded.text(`${__('Loaded')} ${allRows.length}`);
                    lastKey ? $loadBtn.show() : $loadBtn.hide();
                } else {
                    canGrow = false;
                    $loadBtn.hide();
                }
            },
            always: () => {
                isLoading = false;
                $loadBtn.prop('disabled', false);
                $loading.hide();
            }
        });
    }

    /* -------------------- quick-search -------------------- */
    const debounced_search = frappe.utils.debounce(applySearch, 300);
    $('#quick-search').on('input', debounced_search);

    function applySearch() {
        const needle = $('#quick-search').val().trim().toLowerCase();
        filteredRows = needle
            ? allRows.filter(r =>
                (r.item_code || '').toLowerCase().includes(needle) ||
                (r.item_name || '').toLowerCase().includes(needle) ||
                (r.warehouse || '').toLowerCase().includes(needle))
            : allRows;
        renderRows(filteredRows);
        updateTotals();
    }

    function renderRows(rows) {
        const html = rows.map(r => `
            <tr>
                <td>${r.item_code || ''}</td>
                <td>${r.item_name || ''}</td>
                <td>${r.item_group || ''}</td>
                <td>${r.stock_uom || ''}</td>
                <td>${r.warehouse || ''}</td>
                <td class="text-right">${formatNumber(r.balance_qty)}</td>
                <td class="text-right">${formatNumber(r.valuation_rate)}</td>
                <td class="text-right">${formatNumber(r.valuation_amount)}</td>
            </tr>`).join('');
        $tbody.html(html);
    }

    function updateTotals() {
        const tQty = filteredRows.reduce((a, r) => a + flt(r.balance_qty), 0);
        const tValue = filteredRows.reduce((a, r) => a + flt(r.valuation_amount), 0);
        $('#total-qty').text(formatNumber(tQty));
        $('#total-value').text(formatNumber(tValue));
    }

    /* -------------------- helpers -------------------- */
    function formatNumber(v) {
        return flt(v, 2).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    function reset_and_load() { canGrow = true; pageSize = parseInt($('#page-size').val()); fetch(false); }

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
                ['Item Code', 'Item Name', 'Item Group', 'UOM', 'Warehouse', 'Balance Qty', 'Valuation Rate', 'Valuation Amount']
            ];
            filteredRows.forEach(r => ws_data.push([
                r.item_code, r.item_name, r.item_group, r.stock_uom, r.warehouse,
                r.balance_qty, r.valuation_rate, r.valuation_amount
            ]));
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(ws_data), 'Stock Balance');
            XLSX.writeFile(wb, `StockBalance_${frappe.datetime.get_today()}.xlsx`);
        }
    });

    $('#print-pdf').on('click', () => {
        const win = window.open('', 'Print', 'width=1200,height=800');
        win.document.write('<html><head><title>Stock Balance</title>');
        win.document.write('<link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">');
        win.document.write(`<style>body{padding:20px;font-size:12px}tfoot td{font-weight:bold;background:#f8f9fa}</style></head><body>`);
        win.document.write('<h3>Stock Balance Report - ' + frappe.datetime.get_today() + '</h3>');
        win.document.write(document.getElementById('stock-balance-table').outerHTML);
        win.document.write('</body></html>');
        win.document.close();
        setTimeout(() => { win.print(); win.close(); }, 250);
    });

    /* -------------------- keyboard shortcuts -------------------- */
    $(document).on('keydown', function (e) {
        if (e.ctrlKey && e.key === 'e') { e.preventDefault(); $('#export-excel').click(); }
        if (e.ctrlKey && e.key === 'p') { e.preventDefault(); $('#print-pdf').click(); }
    });

    /* -------------------- UI events -------------------- */
    $('#page-size').on('change', reset_and_load);
    $loadBtn.on('click', () => fetch(true));

    /* -------------------- initial load -------------------- */
    fetch(false);
};
