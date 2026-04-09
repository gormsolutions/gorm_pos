(function () {
    function register_handler(page_key, handler) {
        try {
            if (!window.frappe) return false;
            frappe.pages = frappe.pages || {};
            frappe.pages[page_key] = frappe.pages[page_key] || {};
            frappe.pages[page_key].on_page_load = handler;
            return true;
        } catch (e) {
            console.error("register_handler error:", e);
            return false;
        }
    }

    function find_best_page_key() {
        if (!frappe.pages) return null;
        const keys = Object.keys(frappe.pages);
        const candidates = ['expense-report', 'expense_report', 'expenses-by-branch', 'expenses_by_branch'];
        for (let c of candidates) if (frappe.pages[c]) return c;
        for (let k of keys) if (k.toLowerCase().includes('expense')) return k;
        return null;
    }

    function page_handler(wrapper) {
        const page = frappe.ui.make_app_page({
            parent: wrapper,
            title: 'Expense Accounts by Cost Center',
            single_column: true
        });

        const filters = {};
        let last_data = [];
        const reload = frappe.utils.debounce(() => load_data(false), 300);
        const today = frappe.datetime.get_today();

        // --- Filters ---
        filters.from_date = page.add_field({
            label: 'From Date', fieldtype: 'Date',
            default: frappe.datetime.add_days(today, -30), change: reload
        });
        filters.to_date = page.add_field({
            label: 'To Date', fieldtype: 'Date',
            default: today, change: reload
        });
        filters.cost_center = page.add_field({
            label: 'Cost Center', fieldtype: 'Link', options: 'Cost Center', change: reload
        });

        // --- Company ---
        frappe.call({ method: "gormsolutions_mobile_app.custom_api.restrictions.permisions.get_user_companies" })
            .then(r => {
                const companies = r.message || [];
                const opts = companies.length ? companies.join('\n') : ['No Permitted Company'];
                const default_company = companies.length === 1 ? companies[0] : (frappe.defaults.get_default("Company") || companies[0]);
                filters.company = page.add_field({
                    label: 'Company', fieldtype: 'Select', options: opts,
                    default: default_company, change: reload
                });
                try { filters.company.set_value(default_company); } catch(e){}
                load_data();
            }).catch(() => {
                filters.company = page.add_field({
                    label: 'Company', fieldtype: 'Select',
                    options: frappe.defaults.get_default("Company") || '',
                    default: frappe.defaults.get_default("Company"),
                    change: reload
                });
                load_data();
            });

        // --- Container ---
        const $container = $(`
            <div class="mt-3">
                <div class="totals mb-2"></div>
                <div class="report-tree"></div>
            </div>
        `).appendTo(page.body);

        function fmt(v){ return frappe.format(v||0,{fieldtype:'Currency'}); }

        // --- Build tree grouped by parent_account ---
        function build_tree_rows(data) {
            const groups = {};

            // First, group accounts under parent_account
            data.forEach(n => {
                const parent = n.parent_account || n.account; // fallback to account if parent missing
                if (!groups[parent]) groups[parent] = { account_name: parent, amount: 0, children: [] };
                groups[parent].children.push(n);
                groups[parent].amount += parseFloat(n.amount || 0);
            });

            // Convert groups to array
            const group_list = Object.values(groups);

            // Recursive render
            function render(nodes) {
                let html = '<div class="accordion">';
                nodes.forEach((grp, idx) => {
                    const id = `grp_${grp.account_name.replace(/[^a-zA-Z0-9]/g,'_')}_${idx}`;
                    const has_children = grp.children && grp.children.length > 0;
                    if(!has_children && parseFloat(grp.amount)===0) return; // hide empty
                    html += `
                        <div class="card mb-1">
                            <div class="card-header fw-bold d-flex justify-content-between align-items-center" style="cursor:${has_children?'pointer':'default'}" data-target="#${id}">
                                <div>${has_children?'<i class="fa fa-caret-right mr-2 toggle-caret"></i>':'<span style="display:inline-block;width:14px;"></span>'}${frappe.utils.escape_html(grp.account_name)}</div>
                                <div class="text-nowrap"><strong>${fmt(grp.amount)}</strong></div>
                            </div>
                            <div id="${id}" class="collapse">
                                <div class="card-body p-2">
                                    ${has_children?grp.children.map(c=>{
                                        return `
                                            <div class="d-flex justify-content-between border-bottom py-1">
                                                <div>${frappe.utils.escape_html(c.account_name)}</div>
                                                <div><strong>${fmt(c.amount)}</strong></div>
                                            </div>
                                        `;
                                    }).join(''):''}
                                </div>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                return html;
            }

            return render(group_list);
        }

        // --- Load Data ---
        function load_data(download=false){
            const args = {
                from_date: filters.from_date.get_value(),
                to_date: filters.to_date.get_value(),
                cost_center: filters.cost_center.get_value(),
                company: filters.company ? filters.company.get_value() : (frappe.defaults.get_default("Company") || '')
            };

            frappe.dom.freeze("Loading Expense Accounts...");
            frappe.call({
                method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.expenses_by_branch.get_expenses_pnl_style",
                args: args,
                callback: r=>{
                    console.log('Expense Accounts Data:', r);
                    frappe.dom.unfreeze();
                    last_data = r.message || [];
                    const $totals = $container.find('.totals');
                    if(!last_data.length){
                        $container.find('.report-tree').html('<div class="text-center text-muted">No data</div>');
                        $totals.empty(); return;
                    }

                    const total_amount = last_data.reduce((s,a)=>s+parseFloat(a.amount||0),0);
                    $totals.html(`<h5><strong>Total Expenses: ${fmt(total_amount)}</strong></h5>`);

                    $container.find('.report-tree').html(build_tree_rows(last_data));

                    // --- Toggle carets ---
                    $container.find('.card-header').each(function(){
                        const $hdr = $(this);
                        const target = $hdr.data('target');
                        if(!target) return;
                        $hdr.off('click').on('click', function(){
                            const $target = $(target);
                            $target.collapse('toggle');
                            const $caret = $hdr.find('.toggle-caret');
                            $caret.toggleClass('fa-rotate-90');
                        });
                    });

                    // --- Export ---
                    page.clear_menu && page.clear_menu();
                    page.add_menu_item && page.add_menu_item("Export Excel",()=>{
                        if(!last_data.length) return frappe.msgprint("No data");
                        const rows = [["Account","Amount","Parent","Is Group"],...last_data.map(a=>[a.account_name,a.amount,a.parent_account||'',a.is_group?'Yes':'No'])];
                        frappe.tools.downloadify(rows,"Expense_Accounts.xlsx");
                    });

                    page.add_menu_item && page.add_menu_item("Export PDF",()=>{
                        if(!last_data.length) return frappe.msgprint("No data");
                        frappe.require([
                            "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
                            "https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.25/jspdf.plugin.autotable.min.js"
                        ]).then(()=>{
                            const {jsPDF} = window.jspdf;
                            const doc = new jsPDF();
                            const rows = last_data.map(a=>[a.account_name,a.amount,a.parent_account||'',a.is_group?'Yes':'No']);
                            doc.autoTable({head:[["Account","Amount","Parent","Is Group"]],body:rows});
                            doc.save("Expense_Accounts.pdf");
                        });
                    });
                },
                error: ()=>frappe.dom.unfreeze()
            });
        }

        window._expense_report_reload = load_data;
    }

    const best_key = find_best_page_key();
    register_handler(best_key || 'expense-report', page_handler);
})();
