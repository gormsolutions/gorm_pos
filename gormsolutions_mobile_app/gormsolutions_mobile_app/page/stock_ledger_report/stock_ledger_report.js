frappe.pages['stock-ledger-report'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Stock Ledger Report'),
        single_column: true
    });
const today = frappe.datetime.get_today();
const one_month_ago = frappe.datetime.add_months(today, -1);

// get default company from Frappe, fallback to DIVA CAKES
let defaultCompany = frappe.defaults.get_default("company") || "DIVA CAKES";

// set default warehouse based on company
let defaultWarehouse = "";
if (defaultCompany === "CRAVE CITY MEGA LIMITED") {
    defaultWarehouse = "Inventory FGs Shopfloor - Abule Egba (CC)  - CCML";
} else if (defaultCompany === "DIVA CAKES") {
    defaultWarehouse = "ABULEGBA - DC";
}
// add more companies if needed
// else if (defaultCompany === "ANOTHER COMPANY") {
//     defaultWarehouse = "Warehouse Name";
// }

/* -------------------- filters -------------------- */
const filters = {
    company: page.add_field({
        label: __('Company'),
        fieldtype: 'Link',
        options: 'Company',
        default: defaultCompany
    }),
    item_code: page.add_field({ 
        label: __('Item Code'), 
        fieldtype: 'Link', 
        options: 'Item' 
    }),
    item_name: page.add_field({ 
        label: __('Item Name'), 
        fieldtype: 'Data' 
    }),
    item_group: page.add_field({ 
        label: __('Item Group'), 
        fieldtype: 'Link', 
        options: 'Item Group' 
    }),
    warehouse: page.add_field({
        label: __('Warehouse'),
        fieldtype: 'Link',
        options: 'Warehouse',
        default: defaultWarehouse
    }),
    from_date: page.add_field({ 
        label: __('From Date'), 
        fieldtype: 'Date', 
        default: one_month_ago 
    }),
    to_date: page.add_field({ 
        label: __('As of Date'), 
        fieldtype: 'Date', 
        default: today 
    })
};

/* Auto-fetch on any filter change */
Object.values(filters).forEach(f => f.$input.on('change', () => reset_and_load()));


    /* -------------------- table -------------------- */
    const $tableWrap = $(`
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" id="stock-ledger-table">
                <thead class="thead-dark">
                    <tr>
                        <th>${__('Date')}</th><th>${__('Time')}</th><th>${__('Item Code')}</th><th>${__('Item Name')}</th>
                        <th>${__('Item Group')}</th><th>${__('Warehouse')}</th><th class="text-right">${__('Opening Balance')}</th>
                        <th class="text-right">${__('In Qty')}</th><th class="text-right">${__('Out Qty')}</th><th class="text-right">${__('Running Balance')}</th>
                        <th class="text-right">${__('Valuation Rate')}</th><th class="text-right">${__('Valuation Amount')}</th>
                        <th>${__('Voucher Type')}</th><th>${__('Voucher No')}</th>
                    </tr>
                </thead>
                <tbody id="stock-ledger-body"></tbody>
            </table>
        </div>
    `).appendTo(page.body);

   const $tbody = $('#stock-ledger-body');

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
    let lastKey = null;
    let isLoading = false;
    // let pageSize = 10;
    let timerSeconds = 0;
    let timerInterval = null;
    let opening_balances = {};
    let loadedKeys = new Set();

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
    function fetch(next=false){
        if(isLoading) return;
        isLoading = true;

        if(!next){
            lastKey = null; allRows = []; opening_balances = {}; loadedKeys.clear();
            $tbody.empty(); $rowsLoaded.text(''); $loadingSec.text('0s');
        }

        $loading.show();
        startTimer();

        const args = {
            company: filters.company.get_value() || '',
            warehouse: filters.warehouse.get_value() || null,
            items: filters.item_code.get_value() || null,
            search_text: filters.item_name.get_value() || '',
            item_group: filters.item_group.get_value() || '',
            from_date: filters.from_date.get_value() || '',
            to_date: filters.to_date.get_value() || '',
            last_key: lastKey,
            // page_size: pageSize
        };

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.get_stock_ledger_ledger.get_stock_ledger_ledger",
            args: args,
            callback: r=>{
                console.log(r)
                stopTimer();

                if(r.message && r.message.data && r.message.data.length){
                    opening_balances = r.message.opening_balances || {};

                    const newRows = r.message.data.filter(row=>{
                        const uniq = row.name;
                        if(!loadedKeys.has(uniq)){
                            loadedKeys.add(uniq);
                            return true;
                        }
                        return false;
                    });

                    if(newRows.length){
                        allRows = allRows.concat(newRows);
                        renderRows(newRows);
                        $rowsLoaded.text(`Loaded ${allRows.length} rows in ${timerSeconds}s`);
                    } else {
                        $rowsLoaded.text('No more data to load.');
                    }

                    lastKey = r.message.next_key || null;
                    if(!lastKey){
                        $loadBtn.prop('disabled', true);
                    } else {
                        $loadBtn.prop('disabled', false);
                    }
                } else {
                    $rowsLoaded.text('No data to load.');
                    $loadBtn.prop('disabled', true);
                }

                isLoading = false;
                $loading.hide();
            },
            error: ()=>{
                stopTimer();
                $rowsLoaded.text('Error loading data. Please try again.');
                isLoading = false;
                $loadBtn.prop('disabled', false);
                $loading.hide();
            }
        });
    }

    /* -------------------- render rows -------------------- */
    function getVoucherURL(voucher_type, voucher_no){
        const base_url = frappe.urllib.get_base_url();
        const url_type = voucher_type.toLowerCase().replace(/\s+/g,'-');
        return `${base_url}/app/${url_type}/${voucher_no}`;
    }

    function renderRows(rows){
        $tbody.append(rows.map(r => {
            const opening = opening_balances[`${r.item_code}|${r.warehouse}`] || 0;
            return `
                <tr>
                    <td>${r.posting_date}</td>
                    <td>${r.posting_time}</td>
                    <td>${r.item_code}</td>
                    <td>${r.item_name}</td>
                    <td>${r.item_group}</td>
                    <td>${r.warehouse}</td>
                    <td class="text-right">${flt(opening,2).toLocaleString()}</td>
                    <td class="text-right">${flt(r.in_qty,2).toLocaleString()}</td>
                    <td class="text-right">${flt(r.out_qty,2).toLocaleString()}</td>
                    <td class="text-right">${flt(r.running_balance,2).toLocaleString()}</td>
                    <td class="text-right">${flt(r.valuation_rate,2).toLocaleString()}</td>
                    <td class="text-right">${flt(r.valuation_amount,2).toLocaleString()}</td>
                    <td>${r.voucher_type}</td>
                    <td>${r.voucher_no ? `<a href="${getVoucherURL(r.voucher_type,r.voucher_no)}" target="_blank">${r.voucher_no}</a>` : ''}</td>
                </tr>
            `;
        }).join(''));
    }

    /* -------------------- reset + load -------------------- */
    function reset_and_load(){ fetch(false); }

    $loadBtn.on('click', ()=>fetch(true));

    $printBtn.on('click', ()=>{
        const w = window.open('', '_blank');
        w.document.write('<html><head><title>Stock Ledger</title></head><body>');
        w.document.write($('#stock-ledger-table')[0].outerHTML);
        w.document.write('</body></html>');
        w.document.close();
        w.print();
    });

    $excelBtn.on('click', ()=>{
        if(typeof XLSX === 'undefined'){
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
            script.onload = ()=>downloadExcel();
            document.head.appendChild(script);
        } else { downloadExcel(); }

        function downloadExcel(){
            let wb = XLSX.utils.book_new();
            let ws_data = [['Date','Time','Item Code','Item Name','Item Group','Warehouse','Opening Balance','In Qty','Out Qty','Running Balance','Valuation Rate','Valuation Amount','Voucher Type','Voucher No']];
            allRows.forEach(r=>{
                const opening = opening_balances[`${r.item_code}|${r.warehouse}`] || 0;
                ws_data.push([
                    r.posting_date, r.posting_time, r.item_code, r.item_name, r.item_group,
                    r.warehouse, opening, r.in_qty, r.out_qty, r.running_balance,
                    r.valuation_rate, r.valuation_amount, r.voucher_type, r.voucher_no
                ]);
            });
            let ws = XLSX.utils.aoa_to_sheet(ws_data);
            XLSX.utils.book_append_sheet(wb, ws, "Stock Ledger");
            XLSX.writeFile(wb, "Stock_Ledger.xlsx");
        }
    });

    /* -------------------- initial load -------------------- */
    fetch(false);
};
