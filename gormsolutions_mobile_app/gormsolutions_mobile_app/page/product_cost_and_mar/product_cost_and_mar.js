frappe.pages['product-cost-and-mar'].on_page_load = function(wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Product Cost and Margin Report',
		single_column: true
	});

	// Load jsPDF libraries
	frappe.require([
		"https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
		"https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.25/jspdf.plugin.autotable.min.js"
	]);

	// Build UI
	$(`
		<div>
			<div class="flex items-center gap-2 mb-3">
				<input type="text" class="form-control item-filter" placeholder="Search Item Code or Name" style="max-width: 300px;">
				<div class="ml-auto flex gap-2">
					<button class="btn btn-outline-secondary export-excel">Export Excel</button>
					<button class="btn btn-outline-secondary export-pdf">Export PDF</button>
					<button class="btn btn-secondary prev-btn">Previous</button>
					<button class="btn btn-secondary next-btn">Next</button>
				</div>
			</div>
			<div class="table-responsive">
				<table class="table table-bordered table-sm report-table">
					<thead class="table-light">
						<tr>
							<th>Item Code</th>
							<th>Item Name</th>
							<th>Bakery Cost</th>
							<th>Icing Cost</th>
							<th>Total Cost</th>
							<th>Selling Price</th>
							<th>Margin</th>
							<th>Margin %</th>
						</tr>
					</thead>
					<tbody class="report-body"></tbody>
				</table>
			</div>
			<div class="text-muted small mt-2 page-info"></div>
		</div>
	`).appendTo(page.body);

	let limit = 20, offset = 0, current_filter = "", last_data = [];

	function debounce(func, wait) {
		let timeout;
		return function() {
			const context = this, args = arguments;
			clearTimeout(timeout);
			timeout = setTimeout(() => func.apply(context, args), wait);
		}
	}

	function load_data(download=0) {
		frappe.dom.freeze("Loading Product Data...");
		frappe.call({
			method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.products_magins.get_products_with_margins",
			args: { search: current_filter, start: offset, page_length: limit, download: download },
			callback: function(r) {
				let $tbody = $(wrapper).find(".report-body");
				$tbody.empty();
				last_data = r.message || [];

				if (!r.message || !r.message.length) {
					$tbody.append("<tr><td colspan='8' class='text-center text-muted'>No matching items</td></tr>");
					frappe.dom.unfreeze();
					return;
				}

				r.message.forEach(i => {
					$tbody.append(`
						<tr>
							<td><a href="/app/item/${encodeURIComponent(i.item_code)}" target="_blank">${i.item_code}</a></td>
							<td>${frappe.utils.escape_html(i.item_name || "")}</td>
							<td>${frappe.format(i.cost, { fieldtype: 'Currency' })}</td>
							<td>${frappe.format(i.icing_cost, { fieldtype: 'Currency' })}</td>
							<td>${frappe.format(i.total_cost, { fieldtype: 'Currency' })}</td>
							<td>${frappe.format(i.selling_price, { fieldtype: 'Currency' })}</td>
							<td>${frappe.format(i.margin, { fieldtype: 'Currency' })}</td>
							<td>${i.margin_pct}%</td>
						</tr>
					`);
				});

				if(!download) {
					$(wrapper).find(".page-info").text(`Showing ${offset + 1} to ${offset + r.message.length}`);
				}

				frappe.dom.unfreeze();
			}
		});
	}

	// Pagination
	$(wrapper).on("click", ".next-btn", function () { offset += limit; load_data(); });
	$(wrapper).on("click", ".prev-btn", function () { offset = Math.max(0, offset - limit); load_data(); });

	// Search
	$(wrapper).find(".item-filter").on("input", debounce(function () {
		offset = 0;
		current_filter = $(this).val().trim();
		load_data();
	}, 300));

	// Export Excel
	$(wrapper).on("click", ".export-excel", function () {
		frappe.call({
			method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.products_magins.get_products_with_margins",
			args: { search: current_filter, download: 1 },
			callback: function(r) {
				if (!r.message.length) return frappe.msgprint("No data to export.");
				const rows = [
					["Item Code","Item Name","Bakery Cost","Icing Cost","Total Cost","Selling Price","Margin","Margin %"],
					...r.message.map(i => [
						i.item_code,i.item_name,i.cost,i.icing_cost,i.total_cost,i.selling_price,i.margin,i.margin_pct
					])
				];
				frappe.tools.downloadify(rows, "Product_Cost_and_Margin_Report.xlsx");
			}
		});
	});

	// Export PDF
	$(wrapper).on("click", ".export-pdf", function () {
		frappe.call({
			method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.products_magins.get_products_with_margins",
			args: { search: current_filter, download: 1 },
			callback: function(r) {
				if (!r.message.length) return frappe.msgprint("No data to export.");
				const { jsPDF } = window.jspdf;
				const doc = new jsPDF();
				const rows = r.message.map(i => [
					i.item_code,i.item_name,i.cost,i.icing_cost,i.total_cost,i.selling_price,i.margin,i.margin_pct
				]);
				doc.autoTable({ head: [["Item Code","Item Name","Bakery Cost","Icing Cost","Total Cost","Selling Price","Margin","Margin %"]], body: rows });
				doc.save("Product_Cost_and_Margin_Report.pdf");
			}
		});
	});

	// Initial load
	load_data();
};
