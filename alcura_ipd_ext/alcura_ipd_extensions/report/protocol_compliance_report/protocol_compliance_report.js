// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-L4: Protocol Compliance Report with ICU filtering and step drilldown

frappe.query_reports["Protocol Compliance Report"] = {
	filters: [
		{
			fieldname: "protocol_bundle",
			label: __("Protocol Bundle"),
			fieldtype: "Link",
			options: "Monitoring Protocol Bundle",
		},
		{
			fieldname: "category",
			label: __("Category"),
			fieldtype: "Select",
			options: "\nICU\nSepsis\nVentilator\nNutrition\nPressure Injury\nFall Prevention\nOther",
		},
		{
			fieldname: "unit_type",
			label: __("Unit Type"),
			fieldtype: "Select",
			options:
				"\nICU\nCICU\nMICU\nNICU\nPICU\nSICU\nHDU",
			description: __("Filter wards by Healthcare Service Unit Type IPD Room Category"),
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nActive\nCompleted\nDiscontinued\nExpired",
		},
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		if (column.fieldname === "compliance_score") {
			const score = data.compliance_score || 0;
			if (score >= 100) {
				value = `<span class="text-success"><strong>${score}%</strong></span>`;
			} else if (score >= 80) {
				value = `<span class="text-warning"><strong>${score}%</strong></span>`;
			} else {
				value = `<span class="text-danger"><strong>${score}%</strong></span>`;
			}
		}

		if (column.fieldname === "missed_steps" && data.missed_steps > 0) {
			value = `<span class="indicator-pill red">${data.missed_steps}</span>`;
		}

		if (column.fieldname === "delayed_steps" && data.delayed_steps > 0) {
			value = `<span class="indicator-pill orange">${data.delayed_steps}</span>`;
		}

		if (column.fieldname === "active_bundle" && data.active_bundle) {
			value += ` <a class="btn btn-xs btn-default step-detail-btn"
				data-bundle="${data.active_bundle}"
				style="margin-left: 4px"
				title="${__("View Steps")}">
				<i class="fa fa-list"></i>
			</a>`;
		}

		return value;
	},

	onload(report) {
		$(report.wrapper).on("click", ".step-detail-btn", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const bundle = $(this).data("bundle");
			_show_step_detail(bundle);
		});
	},
};

function _show_step_detail(bundle) {
	frappe.call({
		method:
			"alcura_ipd_ext.alcura_ipd_extensions.report.protocol_compliance_report.protocol_compliance_report.get_step_detail",
		args: { active_bundle: bundle },
		freeze: true,
		freeze_message: __("Loading Steps..."),
		callback(r) {
			if (!r.message || !r.message.length) {
				frappe.msgprint(__("No step data found."));
				return;
			}

			const steps = r.message;
			const rows_html = steps
				.map((s) => {
					const status_class =
						s.status === "Completed"
							? "green"
							: s.status === "Missed"
								? "red"
								: s.status === "Pending"
									? "yellow"
									: "grey";

					const delay =
						s.delay_minutes != null && s.delay_minutes > 0
							? `<span class="text-warning">${s.delay_minutes} min</span>`
							: s.delay_minutes === 0
								? "On time"
								: "--";

					return `<tr>
					<td>${s.sequence || ""}</td>
					<td>${frappe.utils.escape_html(s.step_name || "")}</td>
					<td>${frappe.utils.escape_html(s.step_type || "")}</td>
					<td><span class="indicator-pill ${status_class}">${s.status}</span></td>
					<td>${s.is_mandatory ? "Yes" : ""}</td>
					<td>${s.due_at || "--"}</td>
					<td>${s.completed_at || "--"}</td>
					<td>${delay}</td>
					<td>${frappe.utils.escape_html(s.notes || "")}</td>
				</tr>`;
				})
				.join("");

			const d = new frappe.ui.Dialog({
				title: __("Protocol Steps — {0}", [bundle]),
				size: "extra-large",
			});

			d.$body.html(`
			<div style="padding: 10px; overflow-x: auto">
				<table class="table table-bordered table-sm">
					<thead>
						<tr>
							<th>#</th>
							<th>${__("Step")}</th>
							<th>${__("Type")}</th>
							<th>${__("Status")}</th>
							<th>${__("Mandatory")}</th>
							<th>${__("Due At")}</th>
							<th>${__("Completed At")}</th>
							<th>${__("Delay")}</th>
							<th>${__("Notes")}</th>
						</tr>
					</thead>
					<tbody>${rows_html}</tbody>
				</table>
			</div>
		`);

			d.show();
		},
	});
}
