// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-E1: IPD Intake Assessment form enhancements
// - Role-based response visibility
// - Complete Assessment action
// - Quick links to scored Patient Assessments

frappe.ui.form.on("IPD Intake Assessment", {
	refresh(frm) {
		if (frm.is_new()) return;

		_apply_role_visibility(frm);
		_add_action_buttons(frm);
		_show_scored_assessments_section(frm);
		_show_risk_summary(frm);
	},
});

function _apply_role_visibility(frm) {
	if (frm.doc.status === "Completed") {
		frm.disable_save();
	}

	const user_roles = frappe.user_roles || [];
	const is_admin = user_roles.includes("Healthcare Administrator");

	if (is_admin) return;

	const is_nurse = user_roles.includes("Nursing User");
	const is_doctor = user_roles.includes("Physician");

	for (const row of frm.doc.responses || []) {
		const grid_row = frm.fields_dict.responses.grid.grid_rows_by_docname[row.name];
		if (!grid_row) continue;

		// Role visibility from template field metadata is stored
		// in section_label context; we use template to determine visibility
		// For now, all fields are visible; role filtering is applied at
		// template selection level (Nursing vs Physician templates)
	}
}

function _add_action_buttons(frm) {
	if (frm.doc.status === "Completed") {
		frm.dashboard.add_comment(
			__("Assessment completed by {0} on {1}", [
				frm.doc.completed_by,
				frappe.datetime.str_to_user(frm.doc.completed_on),
			]),
			"green",
			true
		);
		return;
	}

	frm.add_custom_button(__("Complete Assessment"), () => {
		frappe.confirm(
			__("Are you sure you want to mark this assessment as Completed? It cannot be modified afterwards."),
			() => {
				frappe.call({
					method: "alcura_ipd_ext.api.intake.complete_assessment",
					args: { assessment: frm.doc.name },
					freeze: true,
					freeze_message: __("Completing assessment..."),
					callback(r) {
						if (r.message) {
							frappe.show_alert({
								message: __("Assessment marked as Completed."),
								indicator: "green",
							});
							frm.reload_doc();
						}
					},
				});
			}
		);
	});
	frm.change_custom_button_type(__("Complete Assessment"), null, "primary");
}

function _show_scored_assessments_section(frm) {
	frappe.call({
		method: "alcura_ipd_ext.api.intake.get_pending_scored",
		args: { assessment: frm.doc.name },
		callback(r) {
			const pending = r.message || [];
			if (!pending.length) return;

			const links = pending.map((pa) => {
				const url = frappe.utils.get_form_link("Patient Assessment", pa.name, true);
				return `<li>${url} — ${pa.assessment_template} <span class="text-warning">(Draft)</span></li>`;
			});

			frm.dashboard.add_comment(
				__("Scored assessments pending completion:") + `<ul>${links.join("")}</ul>`,
				"orange",
				true
			);
		},
	});
}

function _show_risk_summary(frm) {
	if (frm.doc.status !== "Completed" || !frm.doc.inpatient_record) return;

	frappe.call({
		method: "alcura_ipd_ext.api.nursing.get_risk_summary",
		args: { inpatient_record: frm.doc.inpatient_record },
		callback(r) {
			const data = r.message;
			if (!data || !data.updated_on) return;

			const badges = [];

			if (data.allergy_alert) {
				badges.push(`<span class="indicator-pill red">${__("ALLERGY")}: ${frappe.utils.escape_html(data.allergy_summary || "Yes")}</span>`);
			}
			if (data.fall_risk_level) {
				const color = { High: "red", Moderate: "orange", Low: "green" }[data.fall_risk_level] || "grey";
				badges.push(`<span class="indicator-pill ${color}">${__("Fall")}: ${data.fall_risk_level}</span>`);
			}
			if (data.pressure_risk_level) {
				const color = { "Very High": "red", High: "red", Moderate: "orange", Low: "blue", "No Risk": "green" }[data.pressure_risk_level] || "grey";
				badges.push(`<span class="indicator-pill ${color}">${__("Pressure")}: ${data.pressure_risk_level}</span>`);
			}
			if (data.nutrition_risk_level) {
				const color = { High: "red", Medium: "orange", Low: "green" }[data.nutrition_risk_level] || "grey";
				badges.push(`<span class="indicator-pill ${color}">${__("Nutrition")}: ${data.nutrition_risk_level}</span>`);
			}

			if (badges.length) {
				frm.dashboard.add_comment(
					`<strong>${__("Nursing Risk Summary")}:</strong> ${badges.join(" ")}`,
					data.allergy_alert ? "red" : "green",
					true
				);
			}
		},
	});
}
