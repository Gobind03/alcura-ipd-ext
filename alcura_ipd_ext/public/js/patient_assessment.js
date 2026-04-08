// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-E1: Patient Assessment form enhancements for IPD context
// - Show IPD context banner when linked to an intake assessment
// - Quick link back to parent intake assessment
// US-E2: Show risk classification after submission

frappe.ui.form.on("Patient Assessment", {
	refresh(frm) {
		if (frm.is_new()) return;

		_show_ipd_context_banner(frm);
		_show_risk_classification(frm);
	},
});

function _show_ipd_context_banner(frm) {
	if (!frm.doc.custom_inpatient_record) return;

	const ir_link = `<a href="/app/inpatient-record/${frm.doc.custom_inpatient_record}">${frm.doc.custom_inpatient_record}</a>`;
	let msg = __("IPD Assessment for Inpatient Record: {0}", [ir_link]);

	if (frm.doc.custom_intake_assessment) {
		const ia_link = `<a href="/app/ipd-intake-assessment/${frm.doc.custom_intake_assessment}">${frm.doc.custom_intake_assessment}</a>`;
		msg += ` — ${__("Part of Intake: {0}", [ia_link])}`;
	}

	frm.dashboard.add_comment(msg, "blue", true);
}

const _RISK_CLASSIFIERS = {
	"Morse Fall Scale": {
		classify(score) {
			if (score >= 45) return { level: "High", color: "red" };
			if (score >= 25) return { level: "Moderate", color: "orange" };
			return { level: "Low", color: "green" };
		},
		label: __("Fall Risk"),
	},
	"Braden Scale": {
		classify(score) {
			if (score <= 9) return { level: "Very High", color: "red" };
			if (score <= 12) return { level: "High", color: "red" };
			if (score <= 14) return { level: "Moderate", color: "orange" };
			if (score <= 18) return { level: "Low", color: "blue" };
			return { level: "No Risk", color: "green" };
		},
		label: __("Pressure Injury Risk"),
	},
	"MUST Nutritional Screening": {
		classify(score) {
			if (score >= 2) return { level: "High", color: "red" };
			if (score === 1) return { level: "Medium", color: "orange" };
			return { level: "Low", color: "green" };
		},
		label: __("Nutrition Risk"),
	},
};

function _show_risk_classification(frm) {
	if (frm.doc.docstatus !== 1) return;
	if (!frm.doc.custom_inpatient_record) return;

	const template_name = frm.doc.assessment_template;
	const classifier = _RISK_CLASSIFIERS[template_name];
	if (!classifier) return;

	const total = frm.doc.total_score || 0;
	const result = classifier.classify(total);

	frm.dashboard.add_comment(
		`<strong>${classifier.label}:</strong> ${template_name} score ${total} — `
			+ `<span class="indicator-pill ${result.color}">${result.level}</span>`,
		result.color,
		true
	);
}
