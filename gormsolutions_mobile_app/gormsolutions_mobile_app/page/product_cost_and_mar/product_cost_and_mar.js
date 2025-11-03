frappe.pages['product-cost-and-mar'].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Product Cost and Margin Report',
		single_column: true
	});

	// Load jsPDF libraries for PDF export
	frappe.require([
		"https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
		"https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.25/jspdf.plugin.autotable.min.js"
	]);

	// UI structure
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
							<th>Cost (Estimated)</th>
							<th>Selling Price</th>
							<th>Margin (Amount)</th>
							<th>Margin (%)</th>
						</tr>
					</thead>
					<tbody class="report-body"></tbody>
				</table>
			</div>
			<div class="text-muted small mt-2 page-info"></div>
		</div>
	`).appendTo(page.body);

	let limit = 20;
	let offset = 0;
	let current_filter = "";
	let last_data = [];

	// Debounce function
	function debounce(func, wait) {
		let timeout;
		return function() {
			const context = this, args = arguments;
			clearTimeout(timeout);
			timeout = setTimeout(() => func.apply(context, args), wait);
		};
	}

	function load_data(download=0) {
		frappe.dom.freeze("Loading Product Data...");
		frappe.call({
			method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.products_magins.get_products_with_margins",
			args: {
				search: current_filter,
				start: offset,
				page_length: limit,
				download: download
			},
			callback: function (r) {
				let $tbody = $(wrapper).find(".report-body");
				$tbody.empty();
				last_data = r.message || [];

				if (!r.message || !r.message.length) {
					$tbody.append("<tr><td colspan='6' class='text-center text-muted'>No matching items</td></tr>");
					frappe.dom.unfreeze();
					return;
				}

				r.message.forEach(i => {
					let margin = i.selling_price - i.cost;
					let margin_pct = i.cost ? ((margin / i.cost) * 100).toFixed(2) : 0;

					$tbody.append(`
						<tr>
							<td><a href="/app/item/${encodeURIComponent(i.item_code)}" target="_blank">${i.item_code}</a></td>
							<td>${frappe.utils.escape_html(i.item_name || "")}</td>
							<td>${frappe.format(i.cost, { fieldtype: 'Currency' })}</td>
							<td>${frappe.format(i.selling_price, { fieldtype: 'Currency' })}</td>
							<td>${frappe.format(margin, { fieldtype: 'Currency' })}</td>
							<td>${margin_pct}%</td>
						</tr>
					`);
				});

				if(!download) {
					$(wrapper).find(".page-info")
						.text(`Showing ${offset + 1} to ${offset + r.message.length}`);
				}

				frappe.dom.unfreeze();
			}
		});
	}

	// Pagination
	$(wrapper).on("click", ".next-btn", function () {
		offset += limit;
		load_data();
	});
	$(wrapper).on("click", ".prev-btn", function () {
		offset = Math.max(0, offset - limit);
		load_data();
	});

	// Automatic search
	$(wrapper).find(".item-filter").on("input", debounce(function () {
		offset = 0;
		current_filter = $(this).val().trim();
		load_data();
	}, 300));

	// Export Excel (all items)
	$(wrapper).on("click", ".export-excel", function () {
		frappe.call({
			method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.products_magins.get_products_with_margins",
			args: {
				search: current_filter,
				download: 1
			},
			callback: function(r) {
				if (!r.message.length) return frappe.msgprint("No data to export.");

				const rows = [
					["Item Code", "Item Name", "Cost", "Selling Price", "Margin", "Margin %"],
					...r.message.map(i => {
						let margin = i.selling_price - i.cost;
						let margin_pct = i.cost ? ((margin / i.cost) * 100).toFixed(2) : 0;
						return [i.item_code, i.item_name, i.cost, i.selling_price, margin, margin_pct];
					})
				];

				frappe.tools.downloadify(rows, "Product_Cost_and_Margin_Report.xlsx");
			}
		});
	});

	// Export PDF (all items)
	$(wrapper).on("click", ".export-pdf", function () {
		frappe.call({
			method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.products_magins.get_products_with_margins",
			args: {
				search: current_filter,
				download: 1
			},
			callback: function(r) {
				if (!r.message.length) return frappe.msgprint("No data to export.");

				const { jsPDF } = window.jspdf;
				const doc = new jsPDF();
				const rows = r.message.map(i => {
					let margin = i.selling_price - i.cost;
					let margin_pct = i.cost ? ((margin / i.cost) * 100).toFixed(2) : 0;
					return [i.item_code, i.item_name, i.cost, i.selling_price, margin, margin_pct];
				});

				doc.autoTable({
					head: [["Item Code","Item Name","Cost","Selling Price","Margin","Margin %"]],
					body: rows
				});

				doc.save("Product_Cost_and_Margin_Report.pdf");
			}
		});
	});

	// Initial load
	load_data();
};
