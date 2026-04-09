frappe.pages['sales-report'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales Report Spool out ',
        single_column: true
    });

    let filters = {};
    let last_data = [];
    const debounce_reload = frappe.utils.debounce(() => { current_page = 1; load_data(false); }, 500);
    let today = frappe.datetime.get_today();
    let current_page = 1;
    const page_length = 50;

    // --- Filters ---
    filters.from_date = page.add_field({
        label:'From Date',
        fieldtype:'Date',
        default: today,
        change: debounce_reload
    });

    filters.to_date = page.add_field({
        label:'To Date',
        fieldtype:'Date',
        default: today,
        change: debounce_reload
    });

    filters.cost_center = page.add_field({
        label:'Cost Center',
        fieldtype:'Link',
        options:'Cost Center',
        change: debounce_reload
    });

    // Single-select Item Group
    filters.item_group = page.add_field({
        label: 'Item Group',
        fieldtype: 'Link',
        options: 'Item Group',
        change: debounce_reload
    });

    // Company filter
    frappe.call({ method: "gormsolutions_mobile_app.custom_api.restrictions.permisions.get_user_companies" })
    .then(r => {
        const companies = r.message || [];
        const options = companies.length ? companies.join('\n') : ['No Permitted Company'];
        const default_company = companies.length === 1 ? companies[0] : (frappe.defaults.get_default("Company") || companies[0]);

        filters.company = page.add_field({
            label: 'Company',
            fieldtype: 'Select',
            options: options,
            default: default_company,
            reqd: 1,
            change: debounce_reload
        });
        filters.company.set_value(default_company);
        load_data(false);
    });

    // --- Table ---
    const table_html = $(`<div class="mt-3">
        <div class="totals mb-2"></div>
        <div class="table-responsive">
            <table class="table table-bordered table-sm report-table">
                <thead class="table-light">
                    <tr>
                        <th>Item Group</th>
                        <th>SKU</th>
                        <th>Item Name</th>
                        <th>Cost Center</th>
                        <th>Total Qty</th>
                        <th>Total Amount</th>
                    </tr>
                </thead>
                <tbody class="report-body"></tbody>
            </table>
        </div>
        <div class="pagination-controls mt-2"></div>
    </div>`).appendTo(page.body);

    // --- Load Data with Pagination ---
    function load_data(download=false) {
        const args = {
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value(),
            company: filters.company.get_value(),
            cost_center: filters.cost_center.get_value(),
            item_group: filters.item_group.get_value() || '',  // single selection
            download: download ? 1 : 0,
            limit_start: (current_page - 1) * page_length,
            page_length: page_length
        };

        frappe.dom.freeze("Loading Sales Data...");
        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.sales_by_category.get_sales_by_item_group",
            args: args,
            callback: function(r) {
                let $tbody = table_html.find(".report-body");
                let $totals = table_html.find(".totals");
                $tbody.empty();
                last_data = r.message || [];

                if (!last_data.length) {
                    $tbody.append("<tr><td colspan='6' class='text-center text-muted'>No sales found</td></tr>");
                    $totals.empty();
                    update_pagination_controls(false);
                    frappe.dom.unfreeze();
                    return;
                }

                let total_qty = 0, total_amount = 0;
                last_data.forEach(e => {
                    total_qty += parseFloat(e.total_qty || 0);
                    total_amount += parseFloat(e.total_amount || 0);
                    $tbody.append(`
                        <tr>
                            <td>${frappe.utils.escape_html(e.item_group)}</td>
                            <td><a href="/app/item/${encodeURIComponent(e.item_code)}" target="_blank">${e.item_code}</a></td>
                            <td>${frappe.utils.escape_html(e.item_name)}</td>
                            <td>${frappe.utils.escape_html(e.cost_center || "")}</td>
                            <td>${e.total_qty}</td>
                            <td>${frappe.format(e.total_amount, {fieldtype:'Currency'})}</td>
                        </tr>
                    `);
                });

                $totals.html(`<strong>Total Qty: ${total_qty}, Total Amount: ${frappe.format(total_amount, {fieldtype:'Currency'})}</strong>`);
                update_pagination_controls(last_data.length === page_length);
                frappe.dom.unfreeze();
            }
        });
    }

    // --- Pagination Controls ---
    function update_pagination_controls(has_next) {
        const $pagination = table_html.find(".pagination-controls");
        $pagination.empty();

        const prev_disabled = current_page === 1 ? 'disabled' : '';
        const next_disabled = !has_next ? 'disabled' : '';

        $pagination.append(`<button class="btn btn-sm btn-light me-1" ${prev_disabled}>Previous</button>`);
        $pagination.append(`<button class="btn btn-sm btn-light ms-1" ${next_disabled}>Next</button>`);

        $pagination.find("button").first().click(() => {
            if (current_page > 1) { current_page--; load_data(false); }
        });
        $pagination.find("button").last().click(() => {
            if (has_next) { current_page++; load_data(false); }
        });
    }

    // --- Export Menu ---
    page.add_menu_item("Export Excel", () => {
        if (!last_data.length) return frappe.msgprint("No data to export.");
        const rows = [
            ["Item Group","SKU","Item Name","Cost Center","Total Qty","Total Amount"],
            ...last_data.map(e => [e.item_group,e.item_code,e.item_name,e.cost_center,e.total_qty,e.total_amount])
        ];
        frappe.tools.downloadify(rows,"Sales_Report.xlsx");
    });

    page.add_menu_item("Export PDF", () => {
        if (!last_data.length) return frappe.msgprint("No data to export.");
        frappe.require([
            "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.25/jspdf.plugin.autotable.min.js"
        ]).then(() => {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            const rows = last_data.map(e => [e.item_group,e.item_code,e.item_name,e.cost_center,e.total_qty,e.total_amount]);
            doc.autoTable({ head:[["Item Group","SKU","Item Name","Cost Center","Total Qty","Total Amount"]], body: rows });
            doc.save("Sales_Report.pdf");
        });
    });
};
