// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payer Eligibility Check", {
	refresh(frm) {
		_set_indicator(frm);
		_add_status_buttons(frm);
		_set_field_filters(frm);
	},

	patient(frm) {
		if (frm.doc.patient) {
			frm.set_query("patient_payer_profile", () => ({
				filters: { patient: frm.doc.patient, is_active: 1 },
			}));
			frm.set_query("inpatient_record", () => ({
				filters: { patient: frm.doc.patient },
			}));
		}
	},

	patient_payer_profile(frm) {
		if (!frm.doc.patient_payer_profile) {
			frm.set_value("payer_type", "");
			return;
		}
		frappe.db.get_value(
			"Patient Payer Profile",
			frm.doc.patient_payer_profile,
			["payer_type", "room_category_entitlement", "sum_insured"],
			(r) => {
				if (r) {
					frm.set_value("payer_type", r.payer_type);
					if (!frm.doc.approved_room_category && r.room_category_entitlement) {
						frm.set_value("approved_room_category", r.room_category_entitlement);
					}
					if (!frm.doc.approved_amount && r.sum_insured) {
						frm.set_value("approved_amount", r.sum_insured);
					}
				}
			}
		);
	},
});

function _set_indicator(frm) {
	if (frm.is_new()) return;

	const status = frm.doc.verification_status;
	const colors = {
		Pending: "orange",
		Verified: "green",
		Conditional: "blue",
		Rejected: "red",
		Expired: "darkgrey",
	};
	const color = colors[status] || "grey";
	frm.dashboard.set_headline(
		__("{0}", [status]),
		`var(--text-on-${color})`
	);
	frm.page.set_indicator(__(status), color);
}

function _set_field_filters(frm) {
	frm.set_query("patient_payer_profile", () => {
		const filters = { is_active: 1 };
		if (frm.doc.patient) filters.patient = frm.doc.patient;
		return { filters };
	});
	frm.set_query("inpatient_record", () => {
		const filters = {};
		if (frm.doc.patient) filters.patient = frm.doc.patient;
		return { filters };
	});
}

function _add_status_buttons(frm) {
	if (frm.is_new() || frm.is_dirty()) return;

	const status = frm.doc.verification_status;
	const transitions = {
		Pending: ["Verified", "Conditional", "Rejected"],
		Conditional: ["Verified", "Rejected", "Expired"],
		Verified: ["Expired"],
		Rejected: ["Pending"],
		Expired: ["Pending"],
	};

	const labels = {
		Verified: __("Mark Verified"),
		Conditional: __("Mark Conditional"),
		Rejected: __("Mark Rejected"),
		Expired: __("Mark Expired"),
		Pending: __("Re-open for Verification"),
	};

	const allowed = transitions[status] || [];
	allowed.forEach((target) => {
		frm.add_custom_button(
			labels[target] || __(target),
			() => _transition_status(frm, target),
			__("Status")
		);
	});

	if (status === "Pending") {
		frm.change_custom_button_type(
			labels["Verified"],
			__("Status"),
			"primary"
		);
	}
}

function _transition_status(frm, target) {
	const needs_details = ["Verified", "Conditional"].includes(target);

	if (needs_details && !frm.doc.reference_number) {
		frappe.prompt(
			[
				{
					fieldtype: "Data",
					fieldname: "reference_number",
					label: __("Pre-Auth / Reference Number"),
					reqd: 1,
				},
				{
					fieldtype: "Currency",
					fieldname: "approved_amount",
					label: __("Approved Amount"),
					default: frm.doc.approved_amount,
				},
			],
			(values) => {
				frm.set_value("reference_number", values.reference_number);
				if (values.approved_amount) {
					frm.set_value("approved_amount", values.approved_amount);
				}
				frm.set_value("verification_status", target);
				frm.save();
			},
			__("Verification Details"),
			__("Confirm")
		);
		return;
	}

	frappe.confirm(
		__("Change status to {0}?", [frappe.utils.escape_html(target)]),
		() => {
			frm.set_value("verification_status", target);
			frm.save();
		}
	);
}
