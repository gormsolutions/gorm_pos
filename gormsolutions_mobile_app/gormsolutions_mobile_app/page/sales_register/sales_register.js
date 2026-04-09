frappe.pages['sales-register'].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Sales Register',
		single_column: true
	});

	// --- Filters ---
	let filters = {};
	let today = frappe.datetime.get_today();

	filters.from_date = page.add_field({ label: 'From Date', fieldtype: 'Date', default: today, change: () => reload_data() });
	filters.to_date = page.add_field({ label: 'To Date', fieldtype: 'Date', default: today, change: () => reload_data() });
	filters.company = page.add_field({ label: 'Company', fieldtype: 'Link', options: 'Company', default: frappe.defaults.get_default("Company"), change: () => reload_data() });
	filters.customer = page.add_field({ label: 'Customer', fieldtype: 'Link', options: 'Customer', change: () => reload_data() });
	filters.customer_group = page.add_field({ label: 'Customer Group', fieldtype: 'Link', options: 'Customer Group', change: () => reload_data() });
	filters.department = page.add_field({ label: 'Department', fieldtype: 'Link', options: 'Department', change: () => reload_data() });
	filters.invoice = page.add_field({ label: 'Invoice', fieldtype: 'Link', options: 'Sales Invoice', change: () => reload_data() });
	filters.mode_of_payment = page.add_field({ label: 'Mode of Payment', fieldtype: 'Link', options: 'Mode of Payment', change: () => reload_data() });
	filters.cost_center = page.add_field({ label: 'Cost Center', fieldtype: 'Link', options: 'Cost Center', change: () => reload_data() });
	filters.warehouse = page.add_field({ label: 'Warehouse', fieldtype: 'Link', options: 'Warehouse', change: () => reload_data() });
	filters.item_group = page.add_field({ label: 'Item Group', fieldtype: 'Link', options: 'Item Group', change: () => reload_data() });
	filters.owner = page.add_field({ label: 'Owner', fieldtype: 'Link', options: 'User', change: () => reload_data() });

	// --- Buttons ---
	const $buttons = $(`
        <div class="mb-2 text-right">
            <button class="btn btn-secondary" id="export-excel">Export to Excel</button>
            <button class="btn btn-secondary" id="print-pdf">Print PDF</button>
            <button class="btn btn-primary" id="calculate-totals">Recalculate Totals</button>
        </div>
    `).appendTo(page.body);

	// --- Totals ---
	const $totals = $(`
        <div class="mt-2 mb-2 text-right">
            <strong>Total Grand: </strong><span id="total-grand">0.00</span> &nbsp;&nbsp;
            <strong>Total Paid: </strong><span id="total-paid">0.00</span> &nbsp;&nbsp;
            <strong>Total Outstanding: </strong><span id="total-outstanding">0.00</span>
        </div>
    `).appendTo(page.body);

	// --- Table ---
	const $container = $(`
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" id="sales-register-table">
                <thead class="thead-dark">
                    <tr>
                        <th>Invoice</th>
                        <th>Customer</th>
                        <th>Customer Group</th>
                        <th>Mode Of Payment</th>
                        <th>Item Group</th>
                        <th>Cost Center</th>
                        <th>Warehouse</th>
                        <th>Owner</th>
                        <th>Grand Total</th>
                        <th>Paid Amount</th>
                        <th>Outstanding Amount</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody id="sales-register-body"></tbody>
            </table>
        </div>
        <div class="mt-3 text-center">
            <button class="btn btn-outline-primary" id="load-more-btn">Load More</button>
        </div>
    `).appendTo(page.body);

	// --- State ---
	let start = 0, page_length = 50, loading = false;
	const $tbody = $('#sales-register-body');
	const $loadBtn = $('#load-more-btn');
	const $table = $('#sales-register-table');

	// --- Load Data ---
	function load_data(reset = false) {
		if (loading) return;
		if (reset) { $tbody.empty(); start = 0; $loadBtn.prop('disabled', false).text('Load More'); }

		loading = true;
		$loadBtn.text('Loading...');

		frappe.call({
			method: "gormsolutions_mobile_app.custom_api.reports.sales_register.get_sales_register",
			args: {
				from_date: filters.from_date.get_value(),
				to_date: filters.to_date.get_value(),
				company: filters.company.get_value(),
				customer: filters.customer.get_value(),
				customer_group: filters.customer_group.get_value(),
				department: filters.department.get_value(),
				invoice: filters.invoice.get_value(),
				mode_of_payment: filters.mode_of_payment.get_value(),
				cost_center: filters.cost_center.get_value(),
				warehouse: filters.warehouse.get_value(),
				item_group: filters.item_group.get_value(),
				owner: filters.owner.get_value(),
				start: start,
				page_length: page_length
			},
			callback: function (r) {
				if (r.message && r.message.length > 0) {
					const rows = r.message.map(row => `
                        <tr>
                            <td>
            				    ${row.invoice
								? `<a href="/app/sales-invoice/${row.invoice}" target="_blank">${row.invoice}</a>`
								: ''
								}
        					</td>
                            <td>${row.customer || ''}</td>
                            <td>${row.customer_group || ''}</td>
                            <td>${row.mode_of_payment || ''}</td>
                            <td>${row.item_group || ''}</td>
                            <td>${row.cost_center || ''}</td>
                            <td>${row.warehouse || ''}</td>
                            <td>${row.owner || ''}</td>
                            <td class="text-right">${row.grand_total ? parseFloat(row.grand_total).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}) : '0.00'}</td>
                            <td class="text-right">${row.paid_amount ? parseFloat(row.paid_amount).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}) : '0.00'}</td>
                            <td class="text-right">${row.outstanding_amount ? parseFloat(row.outstanding_amount).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}) : '0.00'}</td>
                            <td>${row.posting_date || ''}</td>
                        </tr>
                    `).join('');
					$tbody.append(rows);
					start += page_length;
					$loadBtn.text('Load More');
					calculate_totals(); // auto update totals
				} else {
					$loadBtn.text('No More Records').prop('disabled', true);
				}
				loading = false;
			}
		});
	}
	function reload_data() { load_data(true); }
	$loadBtn.on('click', () => load_data());

	// --- Totals Function ---
	function calculate_totals() {
    let invoice_seen = {}; // keep track of invoices already counted
    let total_grand = 0, total_paid = 0, total_outstanding = 0;

    $('#sales-register-body tr').each(function () {
        let invoice = $(this).find('td').eq(0).text().trim();
        if (!invoice) return;

        // Only sum each invoice once
        if (!invoice_seen[invoice]) {
            invoice_seen[invoice] = true;

            let grand = parseFloat($(this).find('td').eq(8).text().replace(/,/g, '')) || 0;
            let paid = parseFloat($(this).find('td').eq(9).text().replace(/,/g, '')) || 0;
            let outstanding = parseFloat($(this).find('td').eq(10).text().replace(/,/g, '')) || 0;

            total_grand += grand;
            total_paid += paid;
            total_outstanding += outstanding;
        }
    });

    $('#total-grand').text(total_grand.toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}));
    $('#total-paid').text(total_paid.toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}));
    $('#total-outstanding').text(total_outstanding.toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2}));
}


	// --- Print PDF ---
	$('#print-pdf').on('click', function () {
		let printWindow = window.open('', '', 'height=800,width=1200');
		printWindow.document.write('<html><head><title>Sales Register 2</title>');
		printWindow.document.write('<link rel="stylesheet" href="/assets/frappe/css/bootstrap.css">');
		printWindow.document.write('</head><body>');
		printWindow.document.write($table.prop('outerHTML'));
		printWindow.document.write('</body></html>');
		printWindow.document.close();
		setTimeout(() => { printWindow.print(); }, 500);
	});

	// --- Initial Load ---
	load_data(true);
};
