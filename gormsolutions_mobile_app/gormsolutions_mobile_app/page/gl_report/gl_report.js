frappe.pages["gl-report"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "General Ledger",
        single_column: true,
    });

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

    // -------------------- FILTER AREA --------------------
    const filter_area = $(`<div class="gl-filter-box shadow-lg p-4 rounded bg-white d-flex flex-wrap align-items-end gap-3"
        style="border-left: 5px solid #0d6efd; z-index: 100;"></div>`).appendTo(page.body);

    function add_filter(field) {
        const f = page.add_field(field);
        $(f.wrapper).css({ minWidth: "220px", flex: "1 1 220px", marginBottom: "0" });
        filter_area.append(f.wrapper);
        $(f.wrapper).find("input, select").addClass("form-control-sm border-primary shadow-sm");
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
    filters.from_date = add_filter({ label: "From Date", fieldtype: "Date", fieldname: "from_date", default: frappe.datetime.month_start() });
    filters.to_date = add_filter({ label: "To Date", fieldtype: "Date", fieldname: "to_date", default: frappe.datetime.get_today() });

    // -------------------- COMPANY --------------------
    filters.company = add_filter({ label: "Company", fieldtype: "Link", fieldname: "company", options: "Company", reqd: 1 });

    // -------------------- ACCOUNT & COST CENTER --------------------
    filters.account = add_filter({
        label: "Account", fieldtype: "Link", fieldname: "account", options: "Account",
        get_query: () => ({ filters: { company: filters.company.get_value() } })
    });

    filters.cost_center = add_filter({
        label: "Cost Center", fieldtype: "Link", fieldname: "cost_center", options: "Cost Center",
        get_query: () => ({ filters: { company: filters.company.get_value() } })
    });

    // -------------------- VOUCHER TYPE & VOUCHER NO --------------------
    filters.voucher_type = add_filter({ label: "Voucher Type", fieldtype: "Link", fieldname: "voucher_type", options: "DocType" });
    filters.voucher_no = add_filter({ label: "Voucher No", fieldtype: "Data", fieldname: "voucher_no" });

    // -------------------- PARTY TYPE & PARTY --------------------
    filters.party_type = $(`<div class="custom-filter">
        <label for="party_type_select">Party Type</label>
        <select id="party_type_select" class="form-select form-select-sm border-primary shadow-sm">
            <option value="">Select</option>
            <option value="Customer">Customer</option>
            <option value="Supplier">Supplier</option>
        </select>
    </div>`).appendTo(filter_area);

    filters.party_type.get_value = () => $("#party_type_select").val();
    filters.party_type.set_value = val => $("#party_type_select").val(val);

    filters.party = $(`<div class="custom-filter position-relative">
        <label for="party_input">Party</label>
        <input type="text" id="party_input" class="form-control form-control-sm" placeholder="Search Customer/Supplier">
        <div id="party_results" class="list-group position-absolute w-100" style="z-index:1000; max-height:200px; overflow:auto;"></div>
    </div>`).appendTo(filter_area);

    filters.party.get_value = () => $("#party_input").val();
    filters.party.set_value = val => $("#party_input").val(val);

    $("#party_input").on("input", async function () {
        const query = $(this).val();
        const ptype = filters.party_type.get_value();
        const results_container = $("#party_results");

        results_container.empty();
        if (!ptype || !query) return;

        try {
            const res = await frappe.call({
                method: "gormsolutions_mobile_app.custom_api.gl_report_scripts.cost_center.get_parties",
                args: { party_type: ptype, txt: query }
            });

            (res.message || []).forEach(p => {
                const item = $(`<a href="#" class="list-group-item list-group-item-action">${p.value}</a>`);
                item.on("click", e => {
                    e.preventDefault();
                    filters.party.set_value(p.value);
                    results_container.empty();
                });
                results_container.append(item);
            });
        } catch (err) {
            console.error("Error fetching parties:", err);
        }
    });

    filters.company.$input.on("change", () => {
        filters.account.set_value("");
        filters.cost_center.set_value("");
        filters.party.set_value("");
    });

    // -------------------- BUTTONS --------------------
    const run_btn = page.add_button("Run Report", () => {
        offset = 0;
        current_limit_index = 0;
        limit = limits[current_limit_index];
        total_debit = 0;
        total_credit = 0;
        total_entries = 0;
        $("#gl_report_container").empty();
        auto_fetching = true;
        load_ledger_auto();
    }, "primary").addClass("mt-2 px-4 py-2 shadow-sm rounded");

    const action_buttons = $(`<div class="d-flex gap-2 mt-2">
        <button id="print_gl_report" class="btn btn-secondary btn-sm px-3 py-1 shadow-sm rounded">Print</button>
        <button id="download_gl_report" class="btn btn-success btn-sm px-3 py-1 shadow-sm rounded">Download Excel</button>
    </div>`).appendTo(filter_area);

    const report_container = $(`<div id="gl_report_container" class="mt-4"></div>`).appendTo(wrapper);

    // -------------------- PROGRESS BAR --------------------
    const progress_wrapper = $(`<div class="gl-progress-wrapper mb-2">
            <div class="d-flex justify-content-between mb-1">
                <span id="gl_progress_text">Loading...</span>
                <span id="gl_progress_percentage">0%</span>
            </div>
            <div class="progress">
                <div id="gl_progress_bar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%;"></div>
            </div>
        </div>`);

    // -------------------- LOAD LEDGER AUTO --------------------
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
                if ($("#gl_report_table tbody tr").length) {
                    const last_balance_text = $("#gl_report_table tbody tr:last td:nth-child(9)").text() || "";
                    balance = parseFloat(last_balance_text.replace(/,/g, '')) || report_opening_balance;
                } else {
                    balance = report_opening_balance;
                }
            }

            let html = "";

            // Opening totals
            if (offset === 0) {
                html += `<tr class="fw-bold bg-light">
                            <td colspan="6">Opening Totals</td>
                            <td class="text-end">${frappe.format(report_opening_debit, { fieldtype: "Currency" })}</td>
                            <td class="text-end">${frappe.format(report_opening_credit, { fieldtype: "Currency" })}</td>
                            <td class="text-end">${frappe.format(report_opening_balance, { fieldtype: "Currency" })}</td>
                            <td></td>
                         </tr>`;
            }

            let current_group = null;
            let group_debit = 0;
            let group_credit = 0;

            entries.forEach((e) => {
                if (e.group_key !== current_group) {
                    if (current_group !== null) {
                        html += `<tr class="fw-bold bg-secondary text-end text-white">
                                    <td colspan="6" class="text-start">Total for ${current_group}</td>
                                    <td class="text-end">${frappe.format(group_debit, { fieldtype: "Currency" })}</td>
                                    <td class="text-end">${frappe.format(group_credit, { fieldtype: "Currency" })}</td>
                                    <td colspan="2"></td>
                                 </tr>`;
                    }

                    current_group = e.group_key;
                    group_debit = 0;
                    group_credit = 0;

                    html += `<tr class="bg-info text-white group-header" data-group="${current_group}" style="cursor:pointer;">
                                <td colspan="10"><b>${current_group}</b></td>
                             </tr>`;
                }

                balance += (e.debit - e.credit);
                total_debit += e.debit;
                total_credit += e.credit;
                group_debit += e.debit;
                group_credit += e.credit;

                html += `<tr class="align-middle group-row group-${current_group}">
                            <td>${e.posting_date}</td>
                            <td><a href="/app/${(e.voucher_type || "").toLowerCase().replace(/ /g, "-")}/${e.voucher_no}" target="_blank">${e.voucher_no}</a></td>
                            <td>${e.voucher_type || ""}</td>
                            <td>${e.account || ""}</td>
                            <td>${e.party_name || e.party || ""}</td>
                            <td>${e.remarks || ""}</td>
                            <td class="text-end">${frappe.format(e.debit, { fieldtype: "Currency" })}</td>
                            <td class="text-end">${frappe.format(e.credit, { fieldtype: "Currency" })}</td>
                            <td class="text-end">${frappe.format(balance, { fieldtype: "Currency" })}</td>
                            <td>${e.cost_center_name || ""}</td>
                         </tr>`;
            });

            if (current_group !== null) {
                html += `<tr class="fw-bold bg-secondary text-end text-white">
                            <td colspan="6" class="text-start">Total for ${current_group}</td>
                            <td class="text-end">${frappe.format(group_debit, { fieldtype: "Currency" })}</td>
                            <td class="text-end">${frappe.format(group_credit, { fieldtype: "Currency" })}</td>
                            <td colspan="2"></td>
                         </tr>`;
            }

            if ($("#gl_report_table").length) {
                $("#gl_report_table tbody").append(html);
            } else {
                html = `<div class="table-responsive shadow-sm rounded bg-white">
                            <table class="table table-bordered table-hover table-sm mb-0" id="gl_report_table">
                                <thead class="table-light sticky-top">
                                    <tr>
                                        <th>Date</th>
                                        <th>Voucher</th>
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
                                <tbody>` + html + `</tbody>
                            </table>
                        </div>`;
                report_container.html(html);
                report_container.prepend(progress_wrapper);
            }

            $(".group-header").off("click").on("click", function () {
                const group = $(this).data("group");
                $(`.group-${group}`).toggle();
            });

            const fetched_count = Math.min(offset + entries.length, total_entries);
            const percentage = total_entries ? ((fetched_count / total_entries) * 100).toFixed(1) : 100;

            $("#gl_progress_text").text(`Showing ${fetched_count} of ${total_entries} entries`);
            $("#gl_progress_percentage").text(`${percentage}%`);
            $("#gl_progress_bar").css("width", `${percentage}%`);

            if (percentage <= 50) {
                $("#gl_progress_bar").removeClass("bg-warning bg-danger").addClass("bg-success");
            } else if (percentage <= 80) {
                $("#gl_progress_bar").removeClass("bg-success bg-danger").addClass("bg-warning");
            } else {
                $("#gl_progress_bar").removeClass("bg-success bg-warning").addClass("bg-danger");
            }

            if (offset + entries.length < total_entries) {
                offset += entries.length;
                if (current_limit_index < limits.length - 1) current_limit_index++;
                limit = limits[current_limit_index];
                setTimeout(load_ledger_auto, 100);
            } else {
                const difference = total_debit - total_credit;

                const totals_html = `
                    <tr class="fw-bold bg-light text-end">
                        <td colspan="6" class="text-start">Grand Total</td>
                        <td class="text-end">${frappe.format(total_debit, { fieldtype: "Currency" })}</td>
                        <td class="text-end">${frappe.format(total_credit, { fieldtype: "Currency" })}</td>
                        <td class="text-end">${frappe.format(difference, { fieldtype: "Currency" })}</td>
                        <td colspan="2"></td>
                    </tr>

                   <tr class="fw-bold bg-light text-end">
                        <td colspan="6" class="text-start">Closing Totals (Period)</td>
                        <td class="text-end">${frappe.format(report_closing_debit, { fieldtype: "Currency" })}</td>
                        <td class="text-end">${frappe.format(report_closing_credit, { fieldtype: "Currency" })}</td>
                        <td class="text-end">${frappe.format(report_closing_balance, { fieldtype: "Currency" })}</td>
                        <td></td>
                    </tr>`;

                $("#gl_report_table tbody").append(totals_html);
                auto_fetching = false;
            }

        } catch (e) {
            report_container.html(`<div class="text-danger p-3">Error loading data</div>`);
            console.error(e);
            auto_fetching = false;
        }
    };

    frappe.after_ajax(() => {
        if (filters.company.get_value()) {
            offset = 0;
            total_debit = 0;
            total_credit = 0;
            auto_fetching = true;
            $("#gl_report_container").empty();
            load_ledger_auto();
        }
    });

    // -------------------- PRINT --------------------
    $("#print_gl_report").on("click", function () {
        const report_html = document.getElementById("gl_report_container").innerHTML;
        const print_window = window.open("", "_blank", "width=1000,height=800");
        print_window.document.write(`
            <html><head>
                <title>General Ledger</title>
                <link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">
                <style>
                    table { width:100%; border-collapse:collapse; }
                    th,td { border:1px solid #ddd; padding:5px; }
                    th { background:#f8f9fa; position:sticky; top:0; }
                    td.text-end { text-align:right; }
                    td.text-start { text-align:left; }
                    tr.fw-bold { font-weight:600; background:#f1f1f1; }
                </style>
            </head><body><div>${report_html}</div></body></html>`);
        print_window.document.close();
        print_window.print();
    });

    // -------------------- DOWNLOAD EXCEL --------------------
$("#download_gl_report").on("click", function () {
    function export_excel() {
        const table = document.querySelector("#gl_report_table");
        if (!table) return frappe.msgprint("No data to export!");

        // Use SheetJS to convert table to workbook
        const wb = XLSX.utils.table_to_book(table, { sheet: "GL Report" });
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
