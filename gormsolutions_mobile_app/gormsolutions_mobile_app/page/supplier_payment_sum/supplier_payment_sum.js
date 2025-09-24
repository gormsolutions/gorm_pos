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
        })
    };

    Object.values(filters).forEach(f => f.$input.on('change', () => get_data()));

    // container for table
    const $container = $('<div></div>').appendTo(page.body);

    function get_filters() {
        return {
            company: filters.company.get_value(),
            cost_center: filters.cost_center.get_value(),
            supplier: filters.supplier.get_value(),
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value()
        };
    }

    function format_currency(value) {
        return frappe.format(value || 0, { fieldtype: 'Currency' });
    }

    function get_data() {
        if (!filters.company.get_value()) return; // company is mandatory
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
        let html = `
            <table class="table table-bordered table-hover">
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

        data.forEach(row => {
            const voucher_link = row.voucher_no
                ? `<a href="#Form/${encodeURIComponent(row.voucher_type)}/${encodeURIComponent(row.voucher_no)}">${row.voucher_no}</a>`
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

        html += "</tbody></table>";
        $container.html(html);
    }

    page.set_primary_action(__("Refresh"), get_data);

    // first load
    get_data();
};
