frappe.pages['asset_missing_schedu'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Assets without Depreciation Schedule Lines',
        single_column: true
    });

    // Excel download button
    page.set_primary_action(__('Download Excel'), () => exportToExcel());

    // container for count badge + DataTable
    $('<div id="count-badge" style="margin:1rem 0;font-weight:bold;"></div>' +
      '<div class="datatable-wrapper"></div>').appendTo(page.main);

    // initial load
    fetchDataAndRender();

    /* ---------- helpers ---------- */
    function fetchDataAndRender() {
        frappe.call({
            method: 'gormsolutions_mobile_app.custom_api.asset.asset_missing.get_assets_without_schedule_date',
            args: { company: 'DIVA CAKES' },
            callback: (r) => {
                const total = (r.message || []).length;
                $('#count-badge').text(`Total records: ${total}`);
                if (total) {
                    makeDataTable(r.message);
                } else {
                    frappe.msgprint(__('No records found'));
                }
            }
        });
    }

    function makeDataTable(data) {
        const columns = [
            {
                name: 'Asset',
                id: 'asset_name',
                format: (value) => `<a href="/app/asset/${value}" target="_blank">${value}</a>`
            },
            { name: 'Purchase Date', id: 'purchase_date' },
            { name: 'Available-For-Use Date', id: 'available_for_use_date' },
            { name: 'Method', id: 'depreciation_method' },
            { name: 'Frequency (Months)', id: 'frequency_of_depreciation' },
            { name: 'Total Depreciations', id: 'total_number_of_depreciations' },
            // { name: 'Residual', id: 'expected_value_after_useful_life' },
            { name: 'Months Remaining', id: 'months_remaining' }
        ];

        window._table = new frappe.DataTable('.datatable-wrapper', {
            columns: columns,
            data: data,
            layout: 'fluid',
            serialNoColumn: false,
            checkboxColumn: false
        });
    }

    function exportToExcel() {
        if (!window._table || !window._table.datamanager.data.length) {
            frappe.msgprint(__('No data to export'));
            return;
        }
        const rows = window._table.datamanager.data.map(r => ({
            Asset: r.asset_name,
            Purchase_Date: r.purchase_date,
            Available_For_Use_Date: r.available_for_use_date,
            Method: r.depreciation_method,
            Frequency_Months: r.frequency_of_depreciation,
            Total_Depreciations: r.total_number_of_depreciations,
            // Residual_Value: r.expected_value_after_useful_life,
            Months_Remaining: r.months_remaining
        }));
        frappe.tools.downloadify(rows, null, 'Assets_Without_Schedule.xlsx');
    }
};