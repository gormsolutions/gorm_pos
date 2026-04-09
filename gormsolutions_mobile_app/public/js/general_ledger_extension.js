frappe.query_reports["General Ledger"].onload = function (report) {
    report.page.add_inner_button("📤 Export Full Year", function () {
        show_progress_bar();

        frappe.call({
            method: "gormsolutions_mobile_app.custom_api.general_report.general_ledger_download.export_general_ledger",
            args: {
                filters: {
                    from_date: "2025-07-01",
                    to_date: "2025-07-02"
                }
            },
            callback: function (r) {
                if (r.message && r.message.file_url) {
                    simulate_progress(r.message.rows_exported || 3000000, () => {
                        window.open(r.message.file_url);
                        close_progress_bar();
                    });
                } else {
                    close_progress_bar();
                    frappe.msgprint("No file returned.");
                }
            },
            error: function () {
                close_progress_bar();
                frappe.msgprint("There was an error generating the file.");
            }
        });
    });
};

function show_progress_bar() {
    // Remove existing modal if any
    $("#custom-export-modal").remove();
    $(".modal-backdrop").remove();

    const html = `
        <div id="custom-export-modal" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">
            <div class="modal-dialog" role="document" style="max-width: 400px;">
                <div class="modal-content" style="padding: 20px;">
                    <h4>Exporting Data...</h4>
                    <div class="progress mt-3" style="height: 25px;">
                        <div id="export-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated"
                             role="progressbar" style="width: 0%">0%</div>
                    </div>
                    <p class="mt-2" id="row-count-display">Rows processed: 0</p>
                </div>
            </div>
        </div>
        <div class="modal-backdrop fade show"></div>`;

    $("body").append(html);

    // Show modal properly
    $("#custom-export-modal").modal({
        backdrop: 'static',
        keyboard: false,
        show: true
    });
}

function simulate_progress(totalRows, doneCallback) {
    let current = 0;
    const progressBar = document.getElementById("export-progress-bar");
    const rowDisplay = document.getElementById("row-count-display");

    const interval = setInterval(() => {
        const chunk = Math.max(1, Math.floor(totalRows / 100)); // at least 1 row per tick
        current += chunk;

        if (current >= totalRows) {
            current = totalRows;
            clearInterval(interval);
            doneCallback();
        }

        const percent = Math.floor((current / totalRows) * 100);
        progressBar.style.width = `${percent}%`;
        progressBar.innerText = `${percent}%`;
        rowDisplay.innerText = `Rows processed: ${current.toLocaleString()}`;
    }, 50); // update every 50ms
}

function close_progress_bar() {
    // Hide modal and remove backdrop
    $("#custom-export-modal").modal('hide');
    $(".modal-backdrop").remove();
    $("#custom-export-modal").remove();
}
