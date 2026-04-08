// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-E5 / US-L1: Doctor Census report — admitted patients for a practitioner

frappe.query_reports["Doctor Census"] = {
	filters: [
		{
			fieldname: "practitioner",
			label: __("Practitioner"),
			fieldtype: "Link",
			options: "Healthcare Practitioner",
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
		},
		{
			fieldname: "medical_department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Medical Department",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "allergy_alert" && data && data.allergy_alert) {
			value = '<span class="indicator-pill red">ALLERGY</span>';
		}

		if (column.fieldname === "overdue_charts" && data && data.overdue_charts > 0) {
			value = `<span class="indicator-pill red">${data.overdue_charts}</span>`;
		}

		if (column.fieldname === "active_problems" && data && data.active_problems > 0) {
			value = `<span class="indicator-pill orange">${data.active_problems}</span>`;
		}

		if (column.fieldname === "days_admitted" && data && data.days_admitted > 7) {
			value = `<span class="text-danger"><strong>${data.days_admitted}</strong></span>`;
		}

		if (column.fieldname === "pending_tests" && data && data.pending_tests > 0) {
			value = `<span class="indicator-pill blue">${data.pending_tests}</span>`;
		}

		if (column.fieldname === "due_meds" && data && data.due_meds > 0) {
			value = `<span class="indicator-pill orange">${data.due_meds}</span>`;
		}

		if (column.fieldname === "critical_alerts" && data && data.critical_alerts > 0) {
			value = `<span class="indicator-pill red">${data.critical_alerts}</span>`;
		}

		return value;
	},

	onload(report) {
		report.page.add_inner_button(__("Start Round Note"), () => {
			const selected = report.get_checked_items();
			if (!selected.length) {
				frappe.msgprint(__("Please select a patient row first."));
				return;
			}
			const row = selected[0];
			frappe.call({
				method: "alcura_ipd_ext.api.round_sheet.create_round_note",
				args: {
					inpatient_record: row.inpatient_record,
					practitioner: report.get_filter_value("practitioner"),
				},
				freeze: true,
				freeze_message: __("Creating Progress Note..."),
				callback(r) {
					if (r.message) {
						frappe.set_route("Form", "Patient Encounter", r.message.encounter);
					}
				},
			});
		});

		report.page.add_inner_button(__("View Round Summary"), () => {
			const selected = report.get_checked_items();
			if (!selected.length) {
				frappe.msgprint(__("Please select a patient row first."));
				return;
			}
			const row = selected[0];
			frappe.call({
				method: "alcura_ipd_ext.api.round_sheet.get_round_summary",
				args: { inpatient_record: row.inpatient_record },
				freeze: true,
				freeze_message: __("Loading Summary..."),
				callback(r) {
					if (!r.message) return;
					_show_round_summary_dialog(r.message, row);
				},
			});
		});
	},
};

function _show_round_summary_dialog(summary, row) {
	const alerts_html = (summary.alerts || [])
		.map((a) => {
			const color = { red: "red", orange: "orange", green: "green", blue: "blue" }[a.level] || "grey";
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(a.message)}</span>`;
		})
		.join(" ");

	const problems_html = (summary.active_problems || [])
		.map((p, i) => {
			const severity = p.severity ? ` <span class="text-muted">[${frappe.utils.escape_html(p.severity)}]</span>` : "";
			return `<li>${frappe.utils.escape_html(p.problem_description)}${severity}</li>`;
		})
		.join("");

	const pending_labs_html = (summary.pending_lab_tests || [])
		.map((t) => `<li>${frappe.utils.escape_html(t.lab_test_name || t.lab_test_code)} — ${t.status}</li>`)
		.join("");

	const meds = summary.due_medications || {};
	const meds_html = (meds.due_entries || [])
		.map((e) => `<li>${frappe.utils.escape_html(e.medication)} ${e.dose} ${e.route} @ ${e.scheduled_time}</li>`)
		.join("");

	const vitals_html = (summary.recent_vitals || [])
		.map((v) => {
			const crit = v.is_critical ? ' <span class="indicator-pill red">!</span>' : "";
			return `<li>${frappe.utils.escape_html(v.parameter)}: <strong>${v.value}</strong> ${v.uom}${crit}</li>`;
		})
		.join("");

	const notes_html = (summary.recent_notes || [])
		.map((n) => `<li>${n.encounter_date} — ${frappe.utils.escape_html(n.note_type)} by ${frappe.utils.escape_html(n.practitioner_name || "")}</li>`)
		.join("");

	const patient = summary.patient || {};
	const loc = summary.location || {};
	const fluid = summary.fluid_balance || {};

	const d = new frappe.ui.Dialog({
		title: __("{0} — Round Summary", [frappe.utils.escape_html(row.patient_name)]),
		size: "extra-large",
	});

	d.$body.html(`
		<div style="padding: 15px">
			<div class="row mb-3">
				<div class="col-sm-4">
					<strong>${__("Location")}:</strong> ${frappe.utils.escape_html(loc.ward || "")} / ${frappe.utils.escape_html(loc.room || "")} / ${frappe.utils.escape_html(loc.bed || "")}
				</div>
				<div class="col-sm-4">
					<strong>${__("Day")}:</strong> ${patient.days_admitted || ""} &nbsp;
					<strong>${__("Dept")}:</strong> ${frappe.utils.escape_html(patient.department || "")}
				</div>
				<div class="col-sm-4">${alerts_html || '<span class="text-muted">No alerts</span>'}</div>
			</div>
			<div class="row">
				<div class="col-sm-6">
					<h6>${__("Active Problems")}</h6>
					<ul>${problems_html || '<li class="text-muted">None</li>'}</ul>
					<h6>${__("Pending Lab Tests")}</h6>
					<ul>${pending_labs_html || '<li class="text-muted">None</li>'}</ul>
					<h6>${__("Recent Notes")}</h6>
					<ul>${notes_html || '<li class="text-muted">None</li>'}</ul>
				</div>
				<div class="col-sm-6">
					<h6>${__("Recent Vitals")}</h6>
					<ul>${vitals_html || '<li class="text-muted">No vitals recorded</li>'}</ul>
					<h6>${__("Due Medications")} (${meds.due_count || 0} / ${meds.total_today || 0})</h6>
					<ul>${meds_html || '<li class="text-muted">None due</li>'}</ul>
					<h6>${__("Fluid Balance")}</h6>
					<p>
						${__("Intake")}: ${fluid.total_intake || 0} ml &nbsp;
						${__("Output")}: ${fluid.total_output || 0} ml &nbsp;
						${__("Balance")}: ${fluid.balance || 0} ml
					</p>
				</div>
			</div>
		</div>
	`);

	d.show();
}
