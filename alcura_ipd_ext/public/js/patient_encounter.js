// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-D1: Adds "Order IPD Admission" button to the submitted Patient Encounter
// form, allowing the practitioner to create an Inpatient Record with custom
// admission order details (priority, ward, LOS, notes).
// US-E3: Shows IPD clinical context banner (allergies, risks, bed location)
// when the encounter is linked to an Inpatient Record.
// US-E5: Shows Patient Round Summary panel for Progress Notes.

frappe.ui.form.on("Patient Encounter", {
	refresh(frm) {
		_show_ipd_clinical_context(frm);
		_show_round_summary_panel(frm);

		if (frm.doc.docstatus !== 1) return;

		if (frm.doc.custom_ipd_admission_ordered) {
			_show_admission_ordered_banner(frm);
		} else {
			_add_order_admission_button(frm);
		}

		if (frm.doc.custom_linked_inpatient_record) {
			_add_quick_order_button(frm);
		}
	},
});

function _show_admission_ordered_banner(frm) {
	const ir = frm.doc.custom_ipd_inpatient_record;
	const link = ir
		? `<a href="/app/inpatient-record/${ir}">${ir}</a>`
		: __("Unknown");

	frm.dashboard.add_comment(
		__("IPD Admission ordered — Inpatient Record: {0}", [link]),
		"blue",
		true
	);
}

function _add_order_admission_button(frm) {
	frm.add_custom_button(
		__("Order IPD Admission"),
		() => _show_admission_dialog(frm),
		__("Actions")
	);
	frm.change_custom_button_type(
		__("Order IPD Admission"),
		__("Actions"),
		"primary"
	);
}

function _show_admission_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Order IPD Admission"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "patient_info",
				options: `<div class="alert alert-info" style="margin-bottom: 0;">
					<strong>${__("Patient")}:</strong> ${frm.doc.patient_name || frm.doc.patient}
					&nbsp;|&nbsp;
					<strong>${__("Practitioner")}:</strong> ${frm.doc.practitioner_name || frm.doc.practitioner}
				</div>`,
			},
			{ fieldtype: "Section Break", label: __("Admission Details") },
			{
				fieldtype: "Select",
				fieldname: "admission_priority",
				label: __("Admission Priority"),
				options: "Routine\nUrgent\nEmergency",
				default: "Routine",
				reqd: 1,
			},
			{
				fieldtype: "Link",
				fieldname: "requested_ward",
				label: __("Requested Ward"),
				options: "Hospital Ward",
				get_query() {
					const filters = { is_active: 1 };
					if (frm.doc.company) {
						filters.company = frm.doc.company;
					}
					return { filters };
				},
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Int",
				fieldname: "expected_los_days",
				label: __("Expected LOS (Days)"),
				description: __("Expected length of stay in days"),
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Small Text",
				fieldname: "admission_notes",
				label: __("Admission Notes"),
			},
		],
		primary_action_label: __("Order Admission"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.admission.order_ipd_admission",
				args: {
					encounter: frm.doc.name,
					admission_priority: values.admission_priority,
					requested_ward: values.requested_ward || null,
					expected_los_days: values.expected_los_days || null,
					admission_notes: values.admission_notes || null,
				},
				freeze: true,
				freeze_message: __("Creating Inpatient Record..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Inpatient Record {0} created.", [
								r.message.inpatient_record,
							]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		},
	});

	d.show();
}

// ── US-E3: IPD Clinical Context ─────────────────────────────────────

function _show_ipd_clinical_context(frm) {
	const ir = frm.doc.custom_linked_inpatient_record;
	if (!ir) return;

	frm.$wrapper.find(".ipd-clinical-context-banner").remove();

	frappe.call({
		method: "alcura_ipd_ext.api.consultation.get_clinical_context",
		args: { inpatient_record: ir },
		callback(r) {
			if (!r.message) return;
			const ctx = r.message;
			const parts = [];

			const ir_link = `<a href="/app/inpatient-record/${ir}">${ir}</a>`;
			parts.push(`<strong>${__("IPD")}:</strong> ${ir_link}`);

			if (ctx.ward || ctx.room || ctx.bed) {
				const location = [
					ctx.ward ? `${__("Ward")}: ${ctx.ward}` : "",
					ctx.room ? `${__("Room")}: ${ctx.room}` : "",
					ctx.bed ? `${__("Bed")}: ${ctx.bed}` : "",
				].filter(Boolean).join(" | ");
				parts.push(location);
			}

			const pills = [];

			if (ctx.allergy_alert) {
				const summary = ctx.allergy_summary || __("Present");
				pills.push(
					`<span class="indicator-pill red">${__("ALLERGY")}: ${frappe.utils.escape_html(summary)}</span>`
				);
			}

			const risk = ctx.risk_flags || {};
			if (risk.fall) {
				const color = { High: "red", Moderate: "orange", Low: "green" }[risk.fall] || "grey";
				pills.push(`<span class="indicator-pill ${color}">${__("Fall")}: ${risk.fall}</span>`);
			}
			if (risk.pressure) {
				const color = { "Very High": "red", High: "red", Moderate: "orange", Low: "blue", "No Risk": "green" }[risk.pressure] || "grey";
				pills.push(`<span class="indicator-pill ${color}">${__("Pressure")}: ${risk.pressure}</span>`);
			}
			if (risk.nutrition) {
				const color = { High: "red", Medium: "orange", Low: "green" }[risk.nutrition] || "grey";
				pills.push(`<span class="indicator-pill ${color}">${__("Nutrition")}: ${risk.nutrition}</span>`);
			}

			if (pills.length) {
				parts.push(pills.join(" "));
			}

			const banner_color = ctx.allergy_alert ? "red" : "blue";
			frm.dashboard.add_comment(
				parts.join(" &nbsp;|&nbsp; "),
				banner_color,
				true
			);
		},
	});
}

// ── US-E5: Patient Round Summary Panel ──────────────────────────────

function _show_round_summary_panel(frm) {
	const ir = frm.doc.custom_linked_inpatient_record;
	const note_type = frm.doc.custom_ipd_note_type;

	frm.$wrapper.find(".round-summary-panel").remove();

	if (!ir || !note_type) return;
	if (note_type !== "Progress Note" && note_type !== "Admission Note") return;

	frappe.call({
		method: "alcura_ipd_ext.api.round_sheet.get_round_summary",
		args: { inpatient_record: ir },
		callback(r) {
			if (!r.message) return;
			const summary = r.message;
			const html = _build_round_summary_html(summary, ir);

			const $panel = $(`<div class="round-summary-panel">${html}</div>`);
			frm.layout.wrapper.find(".form-message").after($panel);

			$panel.find(".round-panel-section-header").on("click", function () {
				$(this).next(".round-panel-section-body").slideToggle(150);
				$(this).find(".collapse-icon").toggleClass("rotated");
			});

			$panel.find(".btn-add-problem").on("click", () => {
				_show_add_problem_dialog(frm, ir);
			});
		},
	});
}

function _build_round_summary_html(summary, ir) {
	const sections = [];

	// Alerts
	const alerts = summary.alerts || [];
	if (alerts.length) {
		const alertPills = alerts.map(
			(a) => `<span class="indicator-pill ${a.level}">${frappe.utils.escape_html(a.message)}</span>`
		).join(" ");
		sections.push(`<div class="round-panel-alerts" style="margin-bottom: 8px;">${alertPills}</div>`);
	}

	// Active Problems
	const problems = summary.active_problems || [];
	const problemRows = problems.length
		? problems.map((p, i) =>
			`<tr>
				<td>${i + 1}</td>
				<td>${frappe.utils.escape_html(p.problem_description)}</td>
				<td><span class="indicator-pill ${_severity_color(p.severity)}">${p.severity || "-"}</span></td>
				<td>${p.onset_date || "-"}</td>
			</tr>`
		).join("")
		: `<tr><td colspan="4" class="text-muted text-center">${__("No active problems")}</td></tr>`;

	sections.push(_panel_section(
		__("Active Problems"),
		`<table class="table table-sm table-bordered" style="margin-bottom:4px;">
			<thead><tr><th>#</th><th>${__("Problem")}</th><th>${__("Severity")}</th><th>${__("Onset")}</th></tr></thead>
			<tbody>${problemRows}</tbody>
		</table>
		<button class="btn btn-xs btn-default btn-add-problem">${__("+ Add Problem")}</button>`,
		true
	));

	// Recent Vitals
	const vitals = summary.recent_vitals || [];
	if (vitals.length) {
		const vitalPills = vitals.map((v) => {
			const cls = v.is_critical ? "indicator-pill red" : "indicator-pill blue";
			const val = v.value != null ? v.value : "-";
			return `<span class="${cls}"><strong>${frappe.utils.escape_html(v.parameter)}</strong>: ${val} ${frappe.utils.escape_html(v.uom)}</span>`;
		}).join(" ");
		const recordedAt = vitals[0].recorded_at
			? `<span class="text-muted" style="font-size: 0.85em;"> (${frappe.datetime.prettyDate(vitals[0].recorded_at)})</span>`
			: "";
		sections.push(_panel_section(__("Recent Vitals") + recordedAt, `<div>${vitalPills}</div>`));
	}

	// Pending Labs
	const labs = summary.pending_lab_tests || [];
	if (labs.length) {
		const labList = labs.map(
			(l) => `<span class="indicator-pill orange">${frappe.utils.escape_html(l.lab_test_name || l.lab_test_code)} (${l.status})</span>`
		).join(" ");
		sections.push(_panel_section(__("Pending Lab Tests"), `<div>${labList}</div>`));
	}

	// Due Medications
	const meds = summary.due_medications || {};
	if (meds.due_count > 0) {
		const medList = (meds.due_entries || []).map(
			(m) => `<span class="indicator-pill yellow">${frappe.utils.escape_html(m.medication)} ${m.dose} ${m.route} @ ${m.scheduled_time ? frappe.datetime.str_to_user(m.scheduled_time) : "-"}</span>`
		).join(" ");
		sections.push(_panel_section(
			__("Due Medications ({0}/{1})", [meds.due_count, meds.total_today]),
			`<div>${medList}</div>`
		));
	}

	// Fluid Balance
	const fb = summary.fluid_balance || {};
	if (fb.entry_count > 0) {
		const balance_color = fb.balance >= 0 ? "green" : "orange";
		sections.push(_panel_section(
			__("Fluid Balance (Today)"),
			`<span class="indicator-pill blue">${__("In")}: ${fb.total_intake || 0} ml</span>
			 <span class="indicator-pill orange">${__("Out")}: ${fb.total_output || 0} ml</span>
			 <span class="indicator-pill ${balance_color}">${__("Balance")}: ${fb.balance || 0} ml</span>`
		));
	}

	// Recent Notes
	const notes = summary.recent_notes || [];
	if (notes.length) {
		const noteRows = notes.map((n) =>
			`<tr>
				<td>${n.encounter_date || ""}</td>
				<td><span class="indicator-pill grey">${n.note_type || ""}</span></td>
				<td>${frappe.utils.escape_html(n.practitioner_name || "")}</td>
				<td>${frappe.utils.escape_html(n.summary || n.chief_complaint || "")}</td>
			</tr>`
		).join("");
		sections.push(_panel_section(
			__("Recent Notes"),
			`<table class="table table-sm table-bordered">
				<thead><tr><th>${__("Date")}</th><th>${__("Type")}</th><th>${__("Doctor")}</th><th>${__("Summary")}</th></tr></thead>
				<tbody>${noteRows}</tbody>
			</table>`,
			false
		));
	}

	const patient = summary.patient || {};
	const loc = summary.location || {};
	const header = `<div style="display:flex; justify-content:space-between; align-items:center; padding: 8px 12px; background: var(--bg-light-gray); border-bottom: 1px solid var(--border-color);">
		<div>
			<strong>${__("Patient Round Summary")}</strong>
			<span class="text-muted"> — ${__("Day")} ${patient.days_admitted || "?"}</span>
			${loc.ward ? ` | ${__("Ward")}: ${loc.ward}` : ""}
			${loc.bed ? ` | ${__("Bed")}: ${loc.bed}` : ""}
		</div>
		<a href="/app/inpatient-record/${ir}" class="text-muted" style="font-size: 0.85em;">${ir}</a>
	</div>`;

	return `<div style="border: 1px solid var(--border-color); border-radius: var(--border-radius); margin-bottom: 16px; background: var(--card-bg);">
		${header}
		<div style="padding: 8px 12px;">${sections.join("")}</div>
	</div>`;
}

function _panel_section(title, content, startOpen) {
	const openClass = startOpen === false ? ' style="display:none;"' : "";
	const iconClass = startOpen === false ? "" : " rotated";
	return `<div style="margin-bottom: 6px;">
		<div class="round-panel-section-header" style="cursor:pointer; padding: 4px 0; font-weight: 500; font-size: 0.9em; border-bottom: 1px solid var(--border-color); user-select:none;">
			<span class="collapse-icon${iconClass}" style="display:inline-block; transition:transform 0.15s; ${startOpen === false ? "" : "transform:rotate(90deg);"}">&#9654;</span>
			${title}
		</div>
		<div class="round-panel-section-body"${openClass} style="padding: 6px 0;">
			${content}
		</div>
	</div>`;
}

function _severity_color(severity) {
	return { Severe: "red", Moderate: "orange", Mild: "green" }[severity] || "grey";
}

function _show_add_problem_dialog(frm, ir) {
	const d = new frappe.ui.Dialog({
		title: __("Add Problem"),
		fields: [
			{
				fieldtype: "Small Text",
				fieldname: "problem_description",
				label: __("Problem Description"),
				reqd: 1,
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Select",
				fieldname: "severity",
				label: __("Severity"),
				options: "\nMild\nModerate\nSevere",
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Date",
				fieldname: "onset_date",
				label: __("Onset Date"),
				default: frappe.datetime.get_today(),
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Data",
				fieldname: "icd_code",
				label: __("ICD Code"),
			},
		],
		primary_action_label: __("Add"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.round_sheet.add_problem",
				args: {
					inpatient_record: ir,
					problem_description: values.problem_description,
					onset_date: values.onset_date || null,
					severity: values.severity || null,
					icd_code: values.icd_code || null,
					practitioner: frm.doc.practitioner || null,
				},
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Problem added."),
							indicator: "green",
						});
					_show_round_summary_panel(frm);
				}
			},
		});
	},
	});
	d.show();
}

// ── US-F1–F3: Quick Order from Patient Encounter ────────────────────

function _add_quick_order_button(frm) {
	frm.add_custom_button(__("Quick Order"), () => {
		_show_quick_order_dialog(frm);
	}, __("Clinical"));
}

function _show_quick_order_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Place Clinical Order"),
		size: "large",
		fields: [
			{
				fieldtype: "Select", fieldname: "order_type", label: __("Order Type"),
				options: "Medication\nLab Test\nRadiology\nProcedure", reqd: 1,
				change() {
					const type = d.get_value("order_type");
					d.fields_dict.medication_name.toggle(type === "Medication");
					d.fields_dict.lab_test_name.toggle(type === "Lab Test");
					d.fields_dict.procedure_name.toggle(type === "Radiology" || type === "Procedure");
				},
			},
			{
				fieldtype: "Select", fieldname: "urgency", label: __("Urgency"),
				options: "Routine\nUrgent\nSTAT\nEmergency", default: "Routine",
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Data", fieldname: "medication_name", label: __("Medication Name"), hidden: 1 },
			{ fieldtype: "Data", fieldname: "lab_test_name", label: __("Lab Test Name"), hidden: 1 },
			{ fieldtype: "Data", fieldname: "procedure_name", label: __("Procedure Name"), hidden: 1 },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Small Text", fieldname: "clinical_notes", label: __("Clinical Notes") },
		],
		primary_action_label: __("Place Order"),
		primary_action(values) {
			d.hide();
			let method, args;
			const base = {
				patient: frm.doc.patient,
				inpatient_record: frm.doc.custom_linked_inpatient_record,
				urgency: values.urgency,
				ordering_practitioner: frm.doc.practitioner,
				clinical_notes: values.clinical_notes,
			};

			if (values.order_type === "Medication") {
				method = "alcura_ipd_ext.api.clinical_order.create_medication_order";
				args = { ...base, medication_name: values.medication_name };
			} else if (values.order_type === "Lab Test") {
				method = "alcura_ipd_ext.api.clinical_order.create_lab_order";
				args = { ...base, lab_test_name: values.lab_test_name };
			} else {
				method = "alcura_ipd_ext.api.clinical_order.create_procedure_order";
				args = { ...base, procedure_name: values.procedure_name, order_type: values.order_type };
			}

			frappe.call({
				method,
				args,
				freeze: true,
				freeze_message: __("Placing order..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Order {0} placed.", [r.message.order]),
							indicator: "green",
						});
					}
				},
			});
		},
	});
	d.show();
}
