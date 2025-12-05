frappe.pages['budget-vs-actual-spe'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Budget vs Actual Spend per Category',
		single_column: true
	});

	// ---- FILTER SECTION ----
	let filters_wrapper = $(`
		<div class="shadow-sm p-3 bg-white rounded mb-3" style="display:flex;flex-wrap:wrap;gap:15px;">
			<div class="filter-field" data-filter="company"></div>
			<div class="filter-field" data-filter="from_date"></div>
			<div class="filter-field" data-filter="to_date"></div>
			<div class="filter-field" data-filter="cost_center"></div>
			<button class="btn btn-primary" id="run-report" style="height: 38px;">Run Report</button>
		</div>
	`).appendTo(page.body);

	// Create filter controls
	let filters = {
		company: frappe.ui.form.make_control({
			parent: filters_wrapper.find('[data-filter="company"]'),
			df: {
				label: "Company",
				fieldtype: "Link",
				fieldname: "company",
				options: "Company",
				reqd: 1
			},
			render_input: true
		}),

		from_date: frappe.ui.form.make_control({
			parent: filters_wrapper.find('[data-filter="from_date"]'),
			df: {
				label: "From Date",
				fieldtype: "Date",
				fieldname: "from_date",
				reqd: 1
			},
			render_input: true
		}),

		to_date: frappe.ui.form.make_control({
			parent: filters_wrapper.find('[data-filter="to_date"]'),
			df: {
				label: "To Date",
				fieldtype: "Date",
				fieldname: "to_date",
				reqd: 1
			},
			render_input: true
		}),

		cost_center: frappe.ui.form.make_control({
			parent: filters_wrapper.find('[data-filter="cost_center"]'),
			df: {
				label: "Cost Center",
				fieldtype: "Link",
				fieldname: "cost_center",
				options: "Cost Center"
			},
			render_input: true
		})
	};

	// Default Dates
	filters.from_date.set_value(frappe.datetime.add_months(frappe.datetime.get_today(), -1));
	filters.to_date.set_value(frappe.datetime.get_today());

	// ---- TABLE CONTAINER ----
	let table_container = $(`<div class="mt-3"></div>`).appendTo(page.body);

	function run_report() {
		let args = {
			company: filters.company.get_value(),
			from_date: filters.from_date.get_value(),
			to_date: filters.to_date.get_value(),
			cost_center: filters.cost_center.get_value()
		};

		if (!args.company || !args.from_date || !args.to_date) {
			frappe.msgprint("Please fill mandatory filters (Company, From Date, To Date)");
			return;
		}

		frappe.call({
			method: "gormsolutions_mobile_app.custom_api.reports.custom_reports.budget_vs_actual.budget_vs_actual",
			args,
			freeze: true,
			freeze_message: "Fetching Budget vs Actual Data...",
			callback: function(r) {
				if (!r.message) {
					table_container.html(`<div class="alert alert-warning">No data found</div>`);
					return;
				}

				let rows = r.message.map(row => `
					<tr>
						<td>${row.account}</td>
						<td>${row.budget_amount}</td>
						<td>${row.actual_amount}</td>
						<td>${row.variance}</td>
					</tr>
				`).join("");

				table_container.html(`
					<table class="table table-bordered table-striped">
						<thead>
							<tr>
								<th>Category</th>
								<th>Budget Amount</th>
								<th>Actual Spend</th>
								<th>Variance</th>
							</tr>
						</thead>
						<tbody>${rows}</tbody>
					</table>
				`);
			}
		});
	}

	$('#run-report').on("click", run_report);
};
