frappe.pages['supplier-payment-sum'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Supplier Payment Details'),
        single_column: true
    });

    const company = frappe.defaults.get_default("company");

    /* -------------------- filters -------------------- */
    const filters = {
        company: page.add_field({ 
            label: __('Company'), 
            fieldtype: 'Link', 
            options: 'Company', 
            default: company,
            reqd: 1
        }),
        cost_center: page.add_field({ 
            label: __('Cost Center'), 
            fieldtype: 'Link', 
            options: 'Cost Center',
            get_query: () => ({ filters: { company: filters.company.get_value() } })
        }),
        supplier: page.add_field({ 
            label: __('Supplier'), 
            fieldtype: 'Link', 
            options: 'Supplier' 
        }),
        from_date: page.add_field({
            label: __('From Date'),
            fieldtype: 'Date',
            default: frappe.datetime.month_start()
        }),
        to_date: page.add_field({
            label: __('To Date'),
            fieldtype: 'Date',
            default: frappe.datetime.get_today()
        }),
        period: page.add_field({
            label: __('Period'),
            fieldtype: 'Select',
            options: ['', 'Daily', 'Weekly', 'Monthly'],  // "" means no restriction
            default: ''
        })
    };

    Object.values(filters).forEach(f => f.$input.on('change', () => get_data()));

    const $container = $('<div></div>').appendTo(page.body);
    const $buttons = $('<div class="mb-2"></div>').prependTo(page.body);

    function get_filters() {
        return {
            company: filters.company.get_value(),
            cost_center: filters.cost_center.get_value(),
            supplier: filters.supplier.get_value(),
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value(),
            period: filters.period.get_value() || null   // send only if chosen
        };
    }

    function format_currency(value) {
        return frappe.format(value || 0, { fieldtype: 'Currency' });
    }

    function get_data() {
        if (!filters.company.get_value()) return;
        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.supplier_payment_sum.get_supplier_payment_details",
            args: get_filters(),
            callback: function(r) {
                if (r.message && r.message.length) {
                    render_table(r.message);
                } else {
                    $container.html(`<p class="text-muted">${__('No records found')}</p>`);
                }
            }
        });
    }

    function render_table(data) {
        let total_invoice = 0;
        let total_payment = 0;

        const company_name = filters.company.get_value() || "All Companies";
        const from_date = filters.from_date.get_value() || "";
        const to_date = filters.to_date.get_value() || "";
        const period = filters.period.get_value();

        let html = `
            <table class="table table-bordered table-hover" id="supplier-payment-table">
                <thead>
                    <tr>
                        <th>${__('Posting Date')}</th>
                        <th>${__('Voucher Type')}</th>
                        <th>${__('Voucher No')}</th>
                        <th>${__('Supplier')}</th>
                        <th>${__('Full Name')}</th>
                        <th>${__('Company')}</th>
                        <th>${__('Cost Center')}</th>
                        <th class="text-right">${__('Invoice Amount (Debit)')}</th>
                        <th class="text-right">${__('Payment Amount (Credit)')}</th>
                    </tr>
                </thead>
                <tbody>
        `;

        function getVoucherURL(voucher_type, voucher_no){
            const base_url = frappe.urllib.get_base_url();
            const url_type = voucher_type.toLowerCase().replace(/\s+/g,'-');
            return `${base_url}/app/${url_type}/${voucher_no}`;
        }

        data.forEach(row => {
            total_invoice += flt(row.invoice_amount);
            total_payment += flt(row.payment_amount);

            const voucher_link = row.voucher_no
                ? `<a href="${getVoucherURL(row.voucher_type,row.voucher_no)}" target="_blank">${row.voucher_no}</a>`
                : "";

            html += `
                <tr>
                    <td>${row.posting_date || ""}</td>
                    <td>${row.voucher_type || ""}</td>
                    <td>${voucher_link}</td>
                    <td>${row.supplier || ""}</td>
                    <td>${row.supplier_name || ""}</td>
                    <td>${row.company || ""}</td>
                    <td>${row.cost_center || ""}</td>
                    <td class="text-right">${format_currency(row.invoice_amount)}</td>
                    <td class="text-right">${format_currency(row.payment_amount)}</td>
                </tr>
            `;
        });

        html += `
                </tbody>
                <tfoot>
                    <tr>
                        <th colspan="7" class="text-right">${__('Total')}</th>
                        <th class="text-right">${format_currency(total_invoice)}</th>
                        <th class="text-right">${format_currency(total_payment)}</th>
                    </tr>
                </tfoot>
            </table>`;

        $container.html(html);

        $buttons.html(`
            <button class="btn btn-primary btn-sm mr-2" id="print-report">${__('Print')}</button>
            <button class="btn btn-secondary btn-sm" id="download-excel">${__('Download Excel')}</button>
        `);

        // Print
        $('#print-report').on('click', () => {
            const heading = `<h3>${__('Supplier Payment Details for')} ${company_name} (${from_date} → ${to_date}) - ${period}</h3>`;
            let w = window.open();
            w.document.write(`<html><head><title>Supplier Payment Details - ${company_name}</title></head><body>${heading}${$container.html()}</body></html>`);
            w.document.close();
            w.print();
        });

        // Download Excel/CSV
        $('#download-excel').on('click', () => {
            let csv = [];
            const heading = `Supplier Payment Details for ${company_name} (${from_date} → ${to_date}) - ${period}`;
            csv.push([heading].join(","));
            csv.push([]); // blank line
            let headers = ["Posting Date","Voucher Type","Voucher No","Supplier","Full Name","Company","Cost Center","Invoice Amount (Debit)","Payment Amount (Credit)"];
            csv.push(headers.join(","));

            data.forEach(d => {
                csv.push([
                    d.posting_date || "",
                    d.voucher_type || "",
                    d.voucher_no || "",
                    d.supplier || "",
                    d.supplier_name || "",
                    d.company || "",
                    d.cost_center || "",
                    d.invoice_amount || 0,
                    d.payment_amount || 0
                ].join(","));
            });

            csv.push([]); // blank line before totals
            csv.push(["", "", "", "", "", "", "Total", total_invoice, total_payment].join(","));

            const blob = new Blob([csv.join("\n")], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = `Supplier_Payment_${company_name.replace(/ /g, "_")}_${from_date}_to_${to_date}_${period}.csv`;
            link.click();
        });
    }

    page.set_primary_action(__("Refresh"), get_data);

    get_data();
};
