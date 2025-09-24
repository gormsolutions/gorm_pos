frappe.pages['stock-balance-report'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Stock Balance Report'),
        single_column: true
    });

    const today = frappe.datetime.get_today();
    const one_month_ago = frappe.datetime.add_months(today, -1);
    const company = frappe.defaults.get_default("company") || "";

    // set defaults based on company
    let defaultCompany = company;
    let defaultWarehouse = "";

    if (company === "CRAVE CITY MEGA LIMITED") {
        defaultCompany = "CRAVE CITY MEGA LIMITED";
        defaultWarehouse = "Inventory FGs Shopfloor - Abule Egba (CC)  - CCML";
    }
    else if (company === "DIVA CAKES") {
        defaultCompany = "DIVA CAKES";
        defaultWarehouse = "ABULEGBA - DC";
    }

    /* -------------------- filters -------------------- */
    const filters = {
        company: page.add_field({
            label: __('Company'),
            fieldtype: 'Link',
            options: 'Company',
            default: defaultCompany
        }),
        item_code: page.add_field({ label: __('Item Code'), fieldtype: 'Link', options: 'Item' }),
        item_name: page.add_field({ label: __('Item Name'), fieldtype: 'Data' }),
        item_group: page.add_field({ label: __('Item Group'), fieldtype: 'Link', options: 'Item Group' }),
        warehouse: page.add_field({
            label: __('Warehouse'),
            fieldtype: 'Link',
            options: 'Warehouse',
            default: defaultWarehouse
        }),
        from_date: page.add_field({ label: __('From Date'), fieldtype: 'Date', default: one_month_ago }),
        to_date: page.add_field({ label: __('As of Date'), fieldtype: 'Date', default: today })
    };


    /* Auto-fetch on any filter change */
    Object.values(filters).forEach(f => f.$input.on('change', () => reset_and_load()));

    /* -------------------- table -------------------- */
    const $tableWrap = $(`
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" id="stock-balance-table">
                <thead class="thead-dark">
                    <tr>
                        <th>${__('Item Code')}</th><th>${__('Item Name')}</th><th>${__('Item Group')}</th>
                        <th>${__('UOM')}</th><th>${__('Warehouse')}</th>
                        <th class="text-right">${__('Balance Qty')}</th>
                        <th class="text-right">${__('Valuation Rate')}</th>
                        <th class="text-right">${__('Valuation Amount')}</th>
                    </tr>
                </thead>
                <tbody id="stock-balance-body"></tbody>
                <tfoot class="font-weight-bold bg-light">
                    <tr>
                        <td colspan="5">TOTAL (visible rows)</td>
                        <td id="total-qty" class="text-right">0</td><td></td>
                        <td id="total-value" class="text-right">0</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    `).appendTo(page.body);

    const $tbody = $('#stock-balance-body');

    /* -------------------- buttons + status -------------------- */
    const $btnWrap = $('<div class="mb-2 d-flex align-items-center"></div>').prependTo(page.body);
    const $loadBtn = $('<button class="btn btn-secondary btn-sm mr-2">' + __('Load More') + '</button>').appendTo($btnWrap);
    const $printBtn = $('<button class="btn btn-info btn-sm mr-2">' + __('Print') + '</button>').appendTo($btnWrap);
    const $excelBtn = $('<button class="btn btn-success btn-sm mr-2">' + __('Download Excel') + '</button>').appendTo($btnWrap);

    // status indicators moved here
    const $rowsLoaded = $('<span class="ml-3 text-muted"></span>').appendTo($btnWrap);
    const $loading = $('<span class="ml-2 text-muted" style="display:none;">' + __('Loading...') + '</span>').appendTo($btnWrap);
    const $loadingSec = $('<span class="ml-2 text-muted">0s</span>').appendTo($btnWrap);


    /* -------------------- state -------------------- */
    let allRows = [];
    let filteredRows = [];
    let loadedKeys = new Set();
    let lastKey = null;
    let isLoading = false;
    let pageSize = 500;
    let timerSeconds = 0;
    let timerInterval = null;

    function startTimer() {
        clearInterval(timerInterval);
        timerSeconds = 0;
        $loadingSec.text(`${timerSeconds}s`);
        timerInterval = setInterval(() => {
            timerSeconds++;
            $loadingSec.text(`${timerSeconds}s`);
        }, 1000);
    }

    function stopTimer() { clearInterval(timerInterval); }

    /* -------------------- fetch data -------------------- */
    function fetch(next = false) {
        if (isLoading) return;
        isLoading = true;

        if (!next) {
            lastKey = null; allRows = []; filteredRows = []; loadedKeys.clear();
            $tbody.empty(); updateTotals(); $rowsLoaded.text('');
        }

        $loading.show();
        startTimer();

        const args = {
            company: filters.company.get_value() || '',
            warehouse: filters.warehouse.get_value() || '',
            item_code: filters.item_code.get_value() || '',
            item_name: filters.item_name.get_value() || '',
            item_group: filters.item_group.get_value() || '',
            from_date: filters.from_date.get_value() || '',
            to_date: filters.to_date.get_value() || '',
            last_key: lastKey,
            page_size: pageSize
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.stock_balance.get_stock_balances_ledger",
            args: args,
            callback: r => {
                stopTimer();

                let newRows = [];
                if (r.message && r.message.data && r.message.data.length) {
                    r.message.data.forEach(row => {
                        const key = `${row.item_code}|${row.warehouse || 'No Warehouse'}`;
                        if (!loadedKeys.has(key)) {
                            loadedKeys.add(key);
                            newRows.push({ ...row, valuation_amount: flt(row.balance_qty) * flt(row.valuation_rate), warehouse: row.warehouse || 'No Warehouse' });
                        }
                    });

                    if (newRows.length > 0) {
                        allRows = allRows.concat(newRows);
                        applySearch();
                        $rowsLoaded.text(`Loaded ${allRows.length} rows in ${timerSeconds}s`);
                    } else {
                        $rowsLoaded.text('No more data to load.');
                    }

                    // Always enable Load More button
                    $loadBtn.prop('disabled', false);

                    // Update lastKey regardless
                    lastKey = r.message.next_key || null;

                } else {
                    $rowsLoaded.text('No data to load.');
                }

                // Always enable Load More
                $loadBtn.prop('disabled', false);

                isLoading = false;
                $loading.hide();
            },
            error: () => {
                stopTimer();
                $rowsLoaded.text('Error loading data. Please try again.');
                isLoading = false;
                $loadBtn.prop('disabled', false);
                $loading.hide();
            }
        });
    }

    /* -------------------- render rows -------------------- */
    function renderRows(rows) {
        $tbody.html(rows.map(r => `
            <tr>
                <td>${r.item_code || ''}</td><td>${r.item_name || ''}</td><td>${r.item_group || ''}</td>
                <td>${r.stock_uom || ''}</td><td>${r.warehouse || ''}</td>
                <td class="text-right">${flt(r.balance_qty, 2).toLocaleString()}</td>
                <td class="text-right">${flt(r.valuation_rate, 2).toLocaleString()}</td>
                <td class="text-right">${flt(r.valuation_amount, 2).toLocaleString()}</td>
            </tr>
        `).join(''));
    }

    function updateTotals() {
        const tQty = filteredRows.reduce((a, r) => a + flt(r.balance_qty), 0);
        const tValue = filteredRows.reduce((a, r) => a + flt(r.valuation_amount), 0);
        $('#total-qty').text(tQty.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        $('#total-value').text(tValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
    }

    /* -------------------- quick search -------------------- */
    $('#quick-search').on('input', frappe.utils.debounce(() => applySearch(), 300));

    function applySearch() {
        const needle = $('#quick-search').val()?.trim().toLowerCase();
        filteredRows = needle
            ? allRows.filter(r =>
                (r.item_code || '').toLowerCase().includes(needle) ||
                (r.item_name || '').toLowerCase().includes(needle) ||
                (r.warehouse || '').toLowerCase().includes(needle)
            )
            : allRows;
        renderRows(filteredRows);
        updateTotals();
    }

    /* -------------------- reset + load -------------------- */
    function reset_and_load() {
        stopTimer();
        lastKey = null; allRows = []; filteredRows = []; loadedKeys.clear();
        $tbody.empty(); updateTotals(); $rowsLoaded.text('');
        $loadingSec.text('0s');
        fetch(false);
    }

    /* -------------------- button events -------------------- */
    $loadBtn.on('click', () => fetch(true));

    $printBtn.on('click', () => {
        const printWindow = window.open('', '_blank');
        printWindow.document.write('<html><head><title>Stock Balance</title></head><body>');
        printWindow.document.write($('#stock-balance-table')[0].outerHTML);
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        printWindow.print();
    });

    // Load XLSX if not already loaded
    function loadXLSX(callback) {
        if (typeof XLSX !== 'undefined') { callback(); return; }
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
        script.onload = callback;
        document.head.appendChild(script);
    }

    // Excel export button
    $excelBtn.on('click', () => {
        loadXLSX(() => {
            if (typeof XLSX === 'undefined') {
                frappe.msgprint(__('XLSX library not loaded.'));
                return;
            }
            let wb = XLSX.utils.book_new();
            let ws_data = [['Item Code', 'Item Name', 'Item Group', 'UOM', 'Warehouse', 'Balance Qty', 'Valuation Rate', 'Valuation Amount']];
            filteredRows.forEach(r => {
                ws_data.push([r.item_code, r.item_name, r.item_group, r.stock_uom, r.warehouse, r.balance_qty, r.valuation_rate, r.valuation_amount]);
            });
            let ws = XLSX.utils.aoa_to_sheet(ws_data);
            XLSX.utils.book_append_sheet(wb, ws, "Stock Balance");
            XLSX.writeFile(wb, "Stock_Balance.xlsx");
        });
    });

    /* -------------------- initial load -------------------- */
    fetch(false);
};
