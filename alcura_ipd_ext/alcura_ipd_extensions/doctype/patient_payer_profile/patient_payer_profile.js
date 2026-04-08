frappe.ui.form.on("Patient Payer Profile", {
	refresh(frm) {
		_toggle_payer_fields(frm);
		_show_expiry_indicator(frm);
		_set_insurance_policy_filter(frm);
	},

	payer_type(frm) {
		_toggle_payer_fields(frm);
		_clear_irrelevant_fields(frm);
	},

	insurance_payor(frm) {
		_set_insurance_policy_filter(frm);
		if (!frm.doc.insurance_payor) {
			frm.set_value("insurance_policy", "");
			frm.set_value("tpa_name", "");
		}
	},

	patient(frm) {
		_set_insurance_policy_filter(frm);
		if (!frm.doc.patient) {
			frm.set_value("insurance_policy", "");
		}
	},

	insurance_policy(frm) {
		if (frm.doc.insurance_policy) {
			frappe.db.get_value(
				"Patient Insurance Policy",
				frm.doc.insurance_policy,
				["policy_number", "policy_expiry_date"],
				(r) => {
					if (r) {
						if (r.policy_number && !frm.doc.policy_number) {
							frm.set_value("policy_number", r.policy_number);
						}
						if (r.policy_expiry_date && !frm.doc.valid_to) {
							frm.set_value("valid_to", r.policy_expiry_date);
						}
					}
				}
			);
		}
	},

	relationship_to_primary(frm) {
		if (frm.doc.relationship_to_primary === "Self") {
			frm.set_value("primary_holder_name", "");
		}
	},
});

function _toggle_payer_fields(frm) {
	const pt = frm.doc.payer_type;
	const is_tpa = pt === "Insurance TPA";
	const needs_customer = ["Corporate", "PSU"].includes(pt);
	const is_govt = pt === "Government Scheme";
	const is_cash = pt === "Cash";

	frm.toggle_display("payer_details_section", !is_cash);
	frm.toggle_display("member_details_section", !is_cash);

	frm.toggle_display("payer", needs_customer);
	frm.toggle_reqd("payer", needs_customer);

	frm.toggle_display("insurance_payor", is_tpa);
	frm.toggle_reqd("insurance_payor", is_tpa);
	frm.toggle_display("insurance_policy", is_tpa);
	frm.toggle_display("tpa_name", is_tpa);

	frm.toggle_display("employer_name", needs_customer || is_govt);
	frm.toggle_display("scheme_name", is_govt);
}

function _clear_irrelevant_fields(frm) {
	const pt = frm.doc.payer_type;

	if (pt === "Cash") {
		frm.set_value("payer", "");
		frm.set_value("insurance_payor", "");
		frm.set_value("insurance_policy", "");
		frm.set_value("tpa_name", "");
		frm.set_value("employer_name", "");
		frm.set_value("scheme_name", "");
	} else if (["Corporate", "PSU"].includes(pt)) {
		frm.set_value("insurance_payor", "");
		frm.set_value("insurance_policy", "");
		frm.set_value("tpa_name", "");
		if (pt !== "PSU") {
			frm.set_value("scheme_name", "");
		}
	} else if (pt === "Insurance TPA") {
		frm.set_value("payer", "");
		frm.set_value("scheme_name", "");
	} else if (pt === "Government Scheme") {
		frm.set_value("insurance_payor", "");
		frm.set_value("insurance_policy", "");
		frm.set_value("tpa_name", "");
	}
}

function _show_expiry_indicator(frm) {
	if (!frm.doc.valid_to || !frm.doc.is_active) return;

	const valid_to = frappe.datetime.str_to_obj(frm.doc.valid_to);
	const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
	const days_left = frappe.datetime.get_diff(frm.doc.valid_to, frappe.datetime.get_today());

	if (valid_to < today) {
		frm.dashboard.set_headline(
			__("This profile expired on {0}", [frm.doc.valid_to]),
			"red"
		);
	} else if (days_left <= 30) {
		frm.dashboard.set_headline(
			__("This profile expires in {0} day(s)", [days_left]),
			"orange"
		);
	}
}

function _set_insurance_policy_filter(frm) {
	frm.set_query("insurance_policy", () => {
		const filters = {};
		if (frm.doc.patient) {
			filters.patient = frm.doc.patient;
		}
		if (frm.doc.insurance_payor) {
			filters.insurance_payor = frm.doc.insurance_payor;
		}
		return { filters };
	});
}
