frappe.pages['expense-report'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Expenses by Cost Center',
        single_column: true
    });

    let filters = {};
    let last_data = [];

    const debounce_reload = frappe.utils.debounce(() => load_data(false), 500);
    let today = frappe.datetime.get_today();

    // --- Filters ---
    filters.from_date = page.add_field({
        label: 'From Date',
        fieldtype: 'Date',
        default: today,
        change: debounce_reload
    });

    filters.to_date = page.add_field({
        label: 'To Date',
        fieldtype: 'Date',
        default: today,
        change: debounce_reload
    });

    filters.cost_center = page.add_field({
        label: 'Cost Center',
        fieldtype: 'Link',
        options: 'Cost Center',
        change: debounce_reload
    });

    // Fetch permitted companies
    frappe.call({
        method: "gormsolutions_mobile_app.custom_api.restrictions.permisions.get_user_companies",
    }).then(r => {
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
    const table_html = $(`
        <div class="mt-3">
            <div class="totals mb-2"></div>
            <div class="table-responsive">
                <table class="table table-bordered table-sm report-table">
                    <thead class="table-light">
                        <tr>
                            <th>Type</th>
                            <th>Document</th>
                            <th>Account</th>
                            <th>Cost Center</th>
                            <th>Company</th>
                            <th>Amount</th>
                            <th>Posting Date</th>
                        </tr>
                    </thead>
                    <tbody class="report-body"></tbody>
                </table>
            </div>
        </div>
    `).appendTo(page.body);

    // --- Load Data ---
    function load_data(download=false) {
        const args = {
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value(),
            cost_center: filters.cost_center.get_value(),
            company: filters.company.get_value(),
            download: download ? 1 : 0
        };

        frappe.dom.freeze("Loading Expenses...");
        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.expenses_by_branch.get_expenses_by_cost_center",
            args: args,
            callback: function(r) {
                let $tbody = table_html.find(".report-body");
                let $totals = table_html.find(".totals");
                $tbody.empty();
                last_data = r.message || [];

                if (!last_data.length) {
                    $tbody.append("<tr><td colspan='7' class='text-center text-muted'>No expenses found</td></tr>");
                    $totals.empty();
                    frappe.dom.unfreeze();
                    return;
                }

                // Calculate totals
                let total_amount = last_data.reduce((sum, e) => sum + parseFloat(e.amount || 0), 0);
                $totals.html(`<strong>Total Amount: ${frappe.format(total_amount, {fieldtype:'Currency'})}</strong>`);

                last_data.forEach(e => {
                    $tbody.append(`
                        <tr>
                            <td>${e.type}</td>
                            <td><a href="/app/${e.type === "Journal Entry" ? "journal-entry" : "expense-claim"}/${encodeURIComponent(e.document)}" target="_blank">${e.document}</a></td>
                            <td>${frappe.utils.escape_html(e.account)}</td>
                            <td>${frappe.utils.escape_html(e.cost_center)}</td>
                            <td>${frappe.utils.escape_html(e.company)}</td>
                            <td>${frappe.format(e.amount, {fieldtype:'Currency'})}</td>
                            <td>${e.posting_date}</td>
                        </tr>
                    `);
                });

                frappe.dom.unfreeze();
            }
        });
    }

    // --- Export Buttons ---
    page.add_menu_item("Export Excel", () => {
        if (!last_data.length) return frappe.msgprint("No data to export.");
        const rows = [
            ["Type","Document","Account","Cost Center","Company","Amount","Posting Date"],
            ...last_data.map(e => [e.type,e.document,e.account,e.cost_center,e.company,e.amount,e.posting_date])
        ];
        frappe.tools.downloadify(rows, "Expenses_Report.xlsx");
    });

    page.add_menu_item("Export PDF", () => {
        if (!last_data.length) return frappe.msgprint("No data to export.");
        frappe.require([
            "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.25/jspdf.plugin.autotable.min.js"
        ]).then(() => {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            const rows = last_data.map(e => [e.type,e.document,e.account,e.cost_center,e.company,e.amount,e.posting_date]);
            doc.autoTable({ head:[["Type","Document","Account","Cost Center","Company","Amount","Posting Date"]], body: rows });
            doc.save("Expenses_Report.pdf");
        });
    });
};
