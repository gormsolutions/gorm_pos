frappe.pages["gl-report"].on_page_load = function (wrapper) {
    // Professional General Ledger Report with Frappe ERPNext styling
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "General Ledger",
        single_column: true,
    });

    // Add custom CSS for professional styling
    const style = document.createElement('style');
    style.innerHTML = `
        /* Professional GL Report Styling */
        .gl-filter-section {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 24px;
            border: 1px solid var(--border-color, #e2e8f0);
        }
        
        .gl-filter-header {
            padding: 14px 20px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            border-radius: 8px 8px 0 0;
            font-weight: 600;
            color: #1e293b;
            font-size: 14px;
        }
        
        .gl-filter-body {
            padding: 20px;
        }
        
        .gl-report-container {
            background: white;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            overflow-x: auto;
            width: 100%;
            min-height: 200px;
        }
        
        .gl-report-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            min-width: 1200px;
        }
        
        .gl-report-table th {
            background: #f8fafc;
            padding: 12px 12px;
            font-weight: 600;
            color: #334155;
            border-bottom: 1px solid #e2e8f0;
            white-space: nowrap;
        }
        
        .gl-report-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #f1f5f9;
            color: #1e293b;
            vertical-align: top;
        }
        
        /* Column width management */
        .gl-report-table th:nth-child(1), .gl-report-table td:nth-child(1) { width: 90px; } /* Date */
        .gl-report-table th:nth-child(2), .gl-report-table td:nth-child(2) { width: 100px; } /* Voucher No */
        .gl-report-table th:nth-child(3), .gl-report-table td:nth-child(3) { width: 100px; } /* Voucher Type */
        .gl-report-table th:nth-child(4), .gl-report-table td:nth-child(4) { width: 150px; } /* Account */
        .gl-report-table th:nth-child(5), .gl-report-table td:nth-child(5) { width: 120px; } /* Party */
        .gl-report-table th:nth-child(6), .gl-report-table td:nth-child(6) { width: 200px; } /* Remarks */
        .gl-report-table th:nth-child(7), .gl-report-table td:nth-child(7) { width: 100px; } /* Debit */
        .gl-report-table th:nth-child(8), .gl-report-table td:nth-child(8) { width: 100px; } /* Credit */
        .gl-report-table th:nth-child(9), .gl-report-table td:nth-child(9) { width: 100px; } /* Balance */
        .gl-report-table th:nth-child(10), .gl-report-table td:nth-child(10) { width: 120px; } /* Cost Center */
        
        /* Truncate remarks with ellipsis and tooltip on hover */
        .remarks-cell {
            max-width: 200px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            cursor: help;
        }
        
        .remarks-cell:hover {
            white-space: normal;
            word-wrap: break-word;
            background-color: #fff;
            position: absolute;
            z-index: 100;
            width: auto;
            max-width: 400px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            padding: 8px;
            border-radius: 4px;
        }
        
        .gl-report-table tr:hover td {
            background-color: #f8fafc;
        }
        
        .gl-group-header {
            background: #f1f5f9 !important;
            cursor: pointer;
            font-weight: 600;
            color: #0f172a;
        }
        
        .gl-group-header td {
            padding: 10px 12px;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .gl-group-header:hover td {
            background: #e9eef3 !important;
        }
        
        .gl-summary-row {
            background: #fef3c7 !important;
            font-weight: 600;
        }
        
        .gl-grand-total {
            background: #f0fdf4 !important;
            font-weight: 700;
            border-top: 2px solid #22c55e;
        }
        
        .gl-closing-row {
            background: #e0f2fe !important;
            font-weight: 600;
        }
        
        .gl-progress-wrapper {
            padding: 16px 20px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .gl-progress-text {
            font-size: 12px;
            color: #64748b;
            font-weight: 500;
        }
        
        .gl-progress-bar-custom {
            height: 6px;
            border-radius: 3px;
            background: #e2e8f0;
        }
        
        .gl-progress-bar-custom .progress-bar {
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        
        .gl-actions {
            display: flex;
            gap: 8px;
            margin-left: auto;
        }
        
        .gl-filter-row {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            align-items: flex-end;
        }
        
        .gl-filter-field {
            flex: 1;
            min-width: 180px;
        }
        
        .gl-filter-field label {
            font-size: 12px;
            font-weight: 500;
            color: #475569;
            margin-bottom: 4px;
            display: block;
        }
        
        .gl-filter-field select,
        .gl-filter-field input {
            width: 100%;
            border-radius: 6px;
            border: 1px solid #cbd5e1;
            padding: 6px 10px;
            font-size: 13px;
            transition: all 0.2s;
        }
        
        .gl-filter-field select:focus,
        .gl-filter-field input:focus {
            border-color: #3b82f6;
            outline: none;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
        }
        
        .gl-btn-run {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 6px 20px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            height: 34px;
        }
        
        .gl-btn-run:hover {
            background: #2563eb;
        }
        
        .gl-btn-secondary {
            background: white;
            border: 1px solid #cbd5e1;
            padding: 6px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .gl-btn-secondary:hover {
            background: #f8fafc;
            border-color: #94a3b8;
        }
        
        .gl-party-results {
            position: absolute;
            z-index: 1000;
            background: white;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            max-height: 200px;
            overflow-y: auto;
            width: 100%;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        
        .gl-party-results a {
            display: block;
            padding: 8px 12px;
            font-size: 13px;
            color: #1e293b;
            text-decoration: none;
            border-bottom: 1px solid #f1f5f9;
        }
        
        .gl-party-results a:hover {
            background: #f1f5f9;
        }
        
        .text-end {
            text-align: right;
        }
        
        .text-start {
            text-align: left;
        }
        
        .fw-bold {
            font-weight: 600;
        }
        
        .gl-currency {
            font-family: 'SF Mono', monospace;
            font-size: 12px;
        }
        
        .gl-voucher-link {
            color: #3b82f6;
            text-decoration: none;
        }
        
        .gl-voucher-link:hover {
            text-decoration: underline;
        }
        
        .sticky-top {
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        /* Full width layout */
        .page-content {
            padding: 0 !important;
        }
        
        .frappe-control .form-control, .form-control {
            font-size: 13px;
        }
        
        .gl-empty-state {
            text-align: center;
            padding: 50px 20px;
            color: #64748b;
        }
    `;
    document.head.appendChild(style);

    let filters = {};
    let report_opening_balance = 0;
    let report_closing_balance = 0;
    let report_opening_debit = 0;
    let report_opening_credit = 0;
    let report_closing_debit = 0;
    let report_closing_credit = 0;

    let total_debit = 0;
    let total_credit = 0;

    // Pagination variables
    const limits = [200, 700, 1500, 2500];
    let current_limit_index = 0;
    let limit = limits[current_limit_index];
    let offset = 0;
    let total_entries = 0;
    let auto_fetching = false;
    let is_report_loaded = false;

    // Helper function to format date
    function format_date(date_string) {
        if (!date_string) return '';
        try {
            return frappe.datetime.str_to_user(date_string);
        } catch (e) {
            return date_string;
        }
    }
    
    // Helper function to truncate text
    function truncate_text(text, max_length = 50) {
        if (!text) return '';
        if (text.length <= max_length) return text;
        return text.substring(0, max_length) + '...';
    }

    // -------------------- FILTER SECTION --------------------
    const filter_section = $(`
        <div class="gl-filter-section">
            <div class="gl-filter-header">
                <i class="fa fa-filter mr-2"></i> Filters
            </div>
            <div class="gl-filter-body">
                <div class="gl-filter-row" id="gl_filter_row"></div>
                <div class="gl-filter-row mt-3" id="gl_filter_row_actions"></div>
            </div>
        </div>
    `).appendTo(page.body);

    function add_filter(field, row_id = "gl_filter_row") {
        const f = page.add_field(field);
        $(f.wrapper).addClass("gl-filter-field");
        $(`#${row_id}`).append(f.wrapper);
        return f;
    }

    // -------------------- CATEGORIZE BY --------------------
    filters.categorize_by = add_filter({
        fieldname: "categorize_by",
        label: __("Categorize By"),
        fieldtype: "Select",
        options: [
            "",
            "Categorize by Voucher",
            "Categorize by Voucher (Consolidated)",
            "Categorize by Account",
            "Categorize by Party",
        ],
        default: "Categorize by Voucher (Consolidated)",
    });

    // -------------------- DATE FILTERS --------------------
    filters.from_date = add_filter({ 
        label: "From Date", 
        fieldtype: "Date", 
        fieldname: "from_date", 
        default: frappe.datetime.month_start() 
    });
    
    filters.to_date = add_filter({ 
        label: "To Date", 
        fieldtype: "Date", 
        fieldname: "to_date", 
        default: frappe.datetime.get_today() 
    });

    // -------------------- COMPANY --------------------
    filters.company = add_filter({ 
        label: "Company", 
        fieldtype: "Link", 
        fieldname: "company", 
        options: "Company", 
        reqd: 1 
    });

    // -------------------- ACCOUNT & COST CENTER --------------------
    // filters.account = add_filter({
    //     label: "Account", 
    //     fieldtype: "Link", 
    //     fieldname: "account", 
    //     options: "Account",
    //     get_query: () => ({ filters: { company: filters.company.get_value() } })
    // });

    // filters.cost_center = add_filter({
    //     label: "Cost Center", 
    //     fieldtype: "Link", 
    //     fieldname: "cost_center", 
    //     options: "Cost Center",
    //     get_query: () => ({ filters: { company: filters.company.get_value() } })
    // });

        filters.account = add_filter({
    label: "Account",
    fieldtype: "MultiSelectList",
    fieldname: "account",
    get_data: function(txt) {
        return frappe.db.get_link_options(
            "Account",
            txt,
            { company: filters.company.get_value() }
        );
    }
});

filters.cost_center = add_filter({
    label: "Cost Center",
    fieldtype: "MultiSelectList",
    fieldname: "cost_center",
    get_data: function(txt) {
        return frappe.db.get_link_options(
            "Cost Center",
            txt,
            { company: filters.company.get_value() }
        );
    }
});

    // -------------------- VOUCHER TYPE & VOUCHER NO --------------------
    filters.voucher_type = add_filter({ 
        label: "Voucher Type", 
        fieldtype: "Link", 
        fieldname: "voucher_type", 
        options: "DocType" 
    });
    
    filters.voucher_no = add_filter({ 
        label: "Voucher No", 
        fieldtype: "Data", 
        fieldname: "voucher_no" 
    });

    // -------------------- PARTY TYPE & PARTY --------------------

const party_type_wrapper = $(`
    <div class="gl-filter-field">
        <label>Party Type</label>
        <select id="party_type_select" class="form-control">
            <option value="">Select</option>
            <option value="Customer">Customer</option>
            <option value="Supplier">Supplier</option>
        </select>
    </div>
`).appendTo("#gl_filter_row");

filters.party_type = {
    get_value: () => $("#party_type_select").val(),
    set_value: val => $("#party_type_select").val(val)
};


// Party Multi Select
filters.party = add_filter({
    label: "Party",
    fieldtype: "MultiSelectList",
    fieldname: "party",

    get_data: async function (txt) {

        const ptype = filters.party_type.get_value();

        // Require Party Type first
        if (!ptype) {
            frappe.show_alert({
                message: __("Please select Party Type first"),
                indicator: "orange"
            });
            return [];
        }

        try {

            const res = await frappe.call({
                method: "gormsolutions_mobile_app.custom_api.gl_report_scripts.cost_center.get_parties",
                args: {
                    party_type: ptype,
                    txt: txt || ""
                }
            });

            return (res.message || []).map(p => ({
                value: p.value,
                description: p.description
            }));

        } catch (err) {

            console.error("Error fetching parties:", err);

            frappe.show_alert({
                message: __("Error fetching parties"),
                indicator: "red"
            });

            return [];
        }
    }
});


// Clear selected parties when Party Type changes
$("#party_type_select").on("change", function () {

    filters.party.set_value([]);

});
    // Reset dependent filters on company change
    filters.company.$input.on("change", () => {
        filters.account.set_value("");
        filters.cost_center.set_value("");
        filters.party.set_value("");
    });

    // -------------------- ACTION BUTTONS --------------------
    const actions_row = $("#gl_filter_row_actions");
    
    const run_btn = $(`<button class="gl-btn-run" id="run_report_btn">
        <i class="fa fa-play mr-1"></i> Run Report
    </button>`).appendTo(actions_row);
    
    const action_group = $(`<div class="gl-actions"></div>`).appendTo(actions_row);
    
    $(`<button class="gl-btn-secondary" id="print_gl_report">
        <i class="fa fa-print mr-1"></i> Print
    </button>`).appendTo(action_group);
    
    $(`<button class="gl-btn-secondary" id="download_gl_report">
        <i class="fa fa-download mr-1"></i> Excel
    </button>`).appendTo(action_group);

    // -------------------- REPORT CONTAINER --------------------
    const report_container = $(`<div class="gl-report-container"></div>`).appendTo(page.body);
    
    // Show initial empty state
    report_container.html(`
        <div class="gl-empty-state">
            <i class="fa fa-file-text-o" style="font-size: 48px; margin-bottom: 20px;"></i>
            <h4>No Report Loaded</h4>
            <p>Please select a company and click "Run Report" to view the General Ledger.</p>
        </div>
    `);

    // -------------------- PROGRESS BAR --------------------
    const progress_wrapper = $(`
        <div class="gl-progress-wrapper">
            <div class="d-flex justify-content-between mb-2">
                <span class="gl-progress-text" id="gl_progress_text">Loading...</span>
                <span class="gl-progress-text" id="gl_progress_percentage">0%</span>
            </div>
            <div class="gl-progress-bar-custom progress">
                <div id="gl_progress_bar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%; background-color: #3b82f6;"></div>
            </div>
        </div>
    `);

    // -------------------- LOAD LEDGER FUNCTION --------------------
    async function load_ledger_auto() {
        if (!auto_fetching) return;

        const args = {
            from_date: filters.from_date.get_value(),
            to_date: filters.to_date.get_value(),
            company: filters.company.get_value(),
            account: filters.account.get_value(),
            cost_center: filters.cost_center.get_value(),
            party_type: filters.party_type.get_value(),
            party: filters.party.get_value(),
            voucher_type: filters.voucher_type.get_value(),
            voucher_no: filters.voucher_no.get_value(),
            categorize_by: filters.categorize_by.get_value(),
            limit,
            last_name: "",
            offset
        };

        try {
            const res = await frappe.call({
                method: "gormsolutions_mobile_app.gormsolutions_mobile_app.doctype.gl_export.gl_export.fetchy_all_gl_entries",
                args
            });

            const data = res.message || {};
            console.log("Fetched data:", data, args);
            const entries = data.entries || [];
            total_entries = data.total_count || entries.length;

            report_opening_balance = data.opening_balance || 0;
            report_closing_balance = data.closing_balance || 0;
            report_opening_debit = data.opening_debit || 0;
            report_opening_credit = data.opening_credit || 0;
            report_closing_debit = data.closing_debit || 0;
            report_closing_credit = data.closing_credit || 0;

            let balance;
            if (offset === 0) {
                balance = report_opening_balance;
            } else {
                const last_balance_text = $("#gl_report_table tbody tr:last td:nth-child(9)").text() || "";
                balance = parseFloat(last_balance_text.replace(/,/g, '')) || report_opening_balance;
            }

            let html = "";

            // Opening totals row
            if (offset === 0) {
                html += `<tr class="gl-summary-row">
                            <td colspan="6"><strong>Opening Totals</strong></td>
                            <td class="text-end"><strong>${format_currency(report_opening_debit)}</strong></td>
                            <td class="text-end"><strong>${format_currency(report_opening_credit)}</strong></td>
                            <td class="text-end"><strong>${format_currency(report_opening_balance)}</strong></td>
                            <td></td>
                          </tr>`;
            }

            let current_group = null;
            let group_debit = 0;
            let group_credit = 0;

            entries.forEach((e) => {
                if (e.group_key !== current_group) {
                    if (current_group !== null) {
                        html += `<tr class="gl-group-header">
                                    <td colspan="6"><strong>Total for ${current_group}</strong></td>
                                    <td class="text-end"><strong>${format_currency(group_debit)}</strong></td>
                                    <td class="text-end"><strong>${format_currency(group_credit)}</strong></td>
                                    <td colspan="2"></td>
                                  </tr>`;
                    }

                    current_group = e.group_key;
                    group_debit = 0;
                    group_credit = 0;

                    html += `<tr class="gl-group-header" data-group="${current_group ? current_group.replace(/[^a-zA-Z0-9]/g, '_') : 'empty'}">
                                <td colspan="10">
                                    <i class="fa fa-folder-open-o mr-2"></i>
                                    <strong>${current_group || 'Uncategorized'}</strong>
                                    <span class="text-muted ml-2">(click to expand/collapse)</span>
                                </td>
                              </tr>`;
                }

                balance += (e.debit - e.credit);
                total_debit += e.debit;
                total_credit += e.credit;
                group_debit += e.debit;
                group_credit += e.credit;

                const voucher_link = e.voucher_no ? 
                    `<a href="/app/${(e.voucher_type || "").toLowerCase().replace(/ /g, "-")}/${e.voucher_no}" target="_blank" class="gl-voucher-link">${e.voucher_no}</a>` : 
                    "";
                
                const remarks_text = e.remarks || "";
                const truncated_remarks = truncate_text(remarks_text, 60);

                html += `<tr class="group-row group-${current_group ? current_group.replace(/[^a-zA-Z0-9]/g, '_') : 'empty'}">
                            <td>${format_date(e.posting_date)}</td>
                            <td>${voucher_link}</td>
                            <td>${e.voucher_type || ""}</td>
                            <td>${e.account || ""}</td>
                            <td>${e.party_name || e.party || ""}</td>
                            <td class="remarks-cell" title="${remarks_text.replace(/"/g, '&quot;')}">${truncated_remarks}</td>
                            <td class="text-end gl-currency">${format_currency(e.debit)}</td>
                            <td class="text-end gl-currency">${format_currency(e.credit)}</td>
                            <td class="text-end gl-currency"><strong>${format_currency(balance)}</strong></td>
                            <td>${e.cost_center_name || ""}</td>
                          </tr>`;
            });

            if (current_group !== null) {
                html += `<tr class="gl-group-header">
                            <td colspan="6"><strong>Total for ${current_group}</strong></td>
                            <td class="text-end"><strong>${format_currency(group_debit)}</strong></td>
                            <td class="text-end"><strong>${format_currency(group_credit)}</strong></td>
                            <td colspan="2"></td>
                          </tr>`;
            }

            if ($("#gl_report_table").length) {
                $("#gl_report_table tbody").append(html);
            } else {
                const table_html = `
                    <table class="gl-report-table" id="gl_report_table">
                        <thead class="sticky-top">
                            <tr>
                                <th>Date</th>
                                <th>Voucher No</th>
                                <th>Voucher Type</th>
                                <th>Account</th>
                                <th>Party</th>
                                <th>Remarks</th>
                                <th class="text-end">Debit</th>
                                <th class="text-end">Credit</th>
                                <th class="text-end">Balance</th>
                                <th>Cost Center</th>
                            </tr>
                        </thead>
                        <tbody>${html}</tbody>
                    </table>
                `;
                report_container.html(table_html);
                report_container.prepend(progress_wrapper);
            }

            // Group toggle functionality
            $(".gl-group-header[data-group]").off("click").on("click", function() {
                const group = $(this).data("group");
                $(`.group-${group}`).toggle();
                $(this).find(".fa").toggleClass("fa-folder-open-o fa-folder-o");
            });

            const fetched_count = Math.min(offset + entries.length, total_entries);
            const percentage = total_entries ? ((fetched_count / total_entries) * 100).toFixed(1) : 100;

            $("#gl_progress_text").text(`Showing ${fetched_count.toLocaleString()} of ${total_entries.toLocaleString()} entries`);
            $("#gl_progress_percentage").text(`${percentage}%`);
            $("#gl_progress_bar").css("width", `${percentage}%`);

            // Color coding progress bar
            const progress_bar = $("#gl_progress_bar");
            if (percentage <= 50) {
                progress_bar.css("background-color", "#22c55e");
            } else if (percentage <= 80) {
                progress_bar.css("background-color", "#f59e0b");
            } else {
                progress_bar.css("background-color", "#ef4444");
            }

            if (offset + entries.length < total_entries) {
                offset += entries.length;
                if (current_limit_index < limits.length - 1) current_limit_index++;
                limit = limits[current_limit_index];
                setTimeout(load_ledger_auto, 100);
            } else {
                const difference = total_debit - total_credit;

                const totals_html = `
                    <tr class="gl-grand-total">
                        <td colspan="6"><strong>Grand Total</strong></td>
                        <td class="text-end"><strong>${format_currency(total_debit)}</strong></td>
                        <td class="text-end"><strong>${format_currency(total_credit)}</strong></td>
                        <td class="text-end"><strong>${format_currency(difference)}</strong></td>
                        <td></td>
                    </tr>
                    <tr class="gl-closing-row">
                        <td colspan="6"><strong>Closing Totals (Period)</strong></td>
                        <td class="text-end"><strong>${format_currency(report_closing_debit)}</strong></td>
                        <td class="text-end"><strong>${format_currency(report_closing_credit)}</strong></td>
                        <td class="text-end"><strong>${format_currency(report_closing_balance)}</strong></td>
                        <td></td>
                    </tr>`;

                $("#gl_report_table tbody").append(totals_html);
                auto_fetching = false;
                is_report_loaded = true;
                
                // Show success message
                frappe.show_alert({
                    message: __('General Ledger report loaded successfully'),
                    indicator: 'green'
                }, 3);
            }

        } catch (e) {
            report_container.html(`<div class="alert alert-danger m-3">Error loading data: ${e.message || "Unknown error"}</div>`);
            console.error(e);
            auto_fetching = false;
            is_report_loaded = false;
        }
    }

    function format_currency(amount) {
        if (amount === undefined || amount === null) amount = 0;
        return frappe.format(amount, { fieldtype: "Currency" });
    }

    // Run report handler
    run_btn.on("click", () => {
        if (!filters.company.get_value()) {
            frappe.msgprint(__("Please select a Company first"));
            return;
        }
        
        offset = 0;
        current_limit_index = 0;
        limit = limits[current_limit_index];
        total_debit = 0;
        total_credit = 0;
        total_entries = 0;
        is_report_loaded = false;
        report_container.empty();
        auto_fetching = true;
        load_ledger_auto();
    });

    // Auto-load when company is selected initially (only if company has a value)
    setTimeout(() => {
        if (filters.company.get_value()) {
            offset = 0;
            total_debit = 0;
            total_credit = 0;
            is_report_loaded = false;
            auto_fetching = true;
            report_container.empty();
            load_ledger_auto();
        }
    }, 500);

    // -------------------- PRINT FUNCTION --------------------
    $("#print_gl_report").on("click", function () {
        if (!is_report_loaded && !$("#gl_report_table").length) {
            frappe.msgprint({
                title: __('No Data'),
                message: __('Please run the report first by clicking "Run Report" button.'),
                indicator: 'orange'
            });
            return;
        }
        
        const report_container_element = document.getElementById("gl_report_container");
        if (!report_container_element || !$("#gl_report_table").length) {
            frappe.msgprint({
                title: __('No Data'),
                message: __('No report data available to print. Please run the report first.'),
                indicator: 'orange'
            });
            return;
        }
        
        const report_html = report_container_element.innerHTML;
        const title = `General Ledger - ${filters.company.get_value() || "All Companies"}`;
        
        const print_window = window.open("", "_blank", "width=1200,height=800");
        print_window.document.write(`
            <html>
            <head>
                <title>${title}</title>
                <link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">
                <style>
                    body { padding: 20px; font-family: 'Inter', sans-serif; }
                    h2 { color: #1e293b; margin-bottom: 20px; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }
                    table { width: 100%; border-collapse: collapse; font-size: 12px; }
                    th, td { border: 1px solid #e2e8f0; padding: 8px; }
                    th { background: #f8fafc; font-weight: 600; }
                    .text-end { text-align: right; }
                    .text-start { text-align: left; }
                    .gl-summary-row { background: #fef3c7; }
                    .gl-grand-total { background: #f0fdf4; border-top: 2px solid #22c55e; }
                    .gl-closing-row { background: #e0f2fe; }
                    .filter-info { margin-bottom: 20px; font-size: 12px; color: #64748b; }
                    .remarks-cell { max-width: 200px; white-space: normal; word-wrap: break-word; }
                </style>
            </head>
            <body>
                <h2>${title}</h2>
                <div class="filter-info">
                    <strong>Period:</strong> ${filters.from_date.get_value()} to ${filters.to_date.get_value()}<br>
                    <strong>Report Date:</strong> ${frappe.datetime.get_today()}
                </div>
                ${report_html}
            </body>
            </html>
        `);
        print_window.document.close();
        print_window.print();
    });

    // -------------------- EXCEL EXPORT --------------------
    $("#download_gl_report").on("click", function () {
        if (!is_report_loaded && !$("#gl_report_table").length) {
            frappe.msgprint({
                title: __('No Data'),
                message: __('Please run the report first by clicking "Run Report" button.'),
                indicator: 'orange'
            });
            return;
        }
        
function export_excel() {
    const table = document.querySelector("#gl_report_table");

    if (!table) {
        frappe.msgprint({
            title: __('No Data'),
            message: __('No report data available to export. Please run the report first.'),
            indicator: 'orange'
        });
        return;
    }

    let rows = [];

    // ======================
    // HEADER
    // ======================
    rows.push([
        "Date",
        "Voucher No",
        "Voucher Type",
        "Account",
        "Party",
        "Remarks",
        "Debit",
        "Credit",
        "Balance",
        "Cost Center"
    ]);

    // ======================
    // DATA ROWS (CLEAN ONLY)
    // ======================
    $("#gl_report_table tbody tr").each(function () {

        if (
            $(this).hasClass("gl-group-header") ||
            $(this).hasClass("gl-summary-row") ||
            $(this).hasClass("gl-grand-total") ||
            $(this).hasClass("gl-closing-row")
        ) {
            return;
        }

        const tds = $(this).find("td");
        if (tds.length < 10) return;

        rows.push([
            $(tds[0]).text().trim(),
            $(tds[1]).text().trim(),
            $(tds[2]).text().trim(),
            $(tds[3]).text().trim(),
            $(tds[4]).text().trim(),
            $(tds[5]).text().trim(),
            $(tds[6]).text().replace(/,/g, ''),
            $(tds[7]).text().replace(/,/g, ''),
            $(tds[8]).text().replace(/,/g, ''),
            $(tds[9]).text().trim()
        ]);
    });

    // ======================
    // EXTRACT TOTALS FROM PAGE
    // ======================
    const opening_debit = report_opening_debit || 0;
    const opening_credit = report_opening_credit || 0;
    const opening_balance = report_opening_balance || 0;

    const grand_debit = total_debit || 0;
    const grand_credit = total_credit || 0;
    const grand_balance = grand_debit - grand_credit;

    const closing_debit = report_closing_debit || 0;
    const closing_credit = report_closing_credit || 0;
    const closing_balance = report_closing_balance || 0;

    // ======================
    // EMPTY ROW SPACER
    // ======================
    rows.push([]);

    // ======================
    // OPENING TOTALS
    // ======================
    rows.push([
        "OPENING TOTALS",
        "",
        "",
        "",
        "",
        "",
        opening_debit,
        opening_credit,
        opening_balance,
        ""
    ]);

    // ======================
    // GRAND TOTAL
    // ======================
    rows.push([
        "GRAND TOTAL",
        "",
        "",
        "",
        "",
        "",
        grand_debit,
        grand_credit,
        grand_balance,
        ""
    ]);

    // ======================
    // CLOSING TOTALS
    // ======================
    rows.push([
        "CLOSING TOTAL (PERIOD)",
        "",
        "",
        "",
        "",
        "",
        closing_debit,
        closing_credit,
        closing_balance,
        ""
    ]);

    // ======================
    // BUILD EXCEL SHEET
    // ======================
    const ws = XLSX.utils.aoa_to_sheet(rows);

    ws["!cols"] = [
        { wch: 15 }, // Date
        { wch: 18 }, // Voucher No
        { wch: 18 }, // Voucher Type
        { wch: 25 }, // Account
        { wch: 20 }, // Party
        { wch: 40 }, // Remarks
        { wch: 15 }, // Debit
        { wch: 15 }, // Credit
        { wch: 15 }, // Balance
        { wch: 20 }  // Cost Center
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "General Ledger");

    XLSX.writeFile(wb, `General_Ledger_${frappe.datetime.get_today()}.xlsx`);
}

        if (typeof XLSX === "undefined") {
            let script = document.createElement("script");
            script.src = "https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js";
            script.onload = export_excel;
            document.head.appendChild(script);
        } else {
            export_excel();
        }
    });
};