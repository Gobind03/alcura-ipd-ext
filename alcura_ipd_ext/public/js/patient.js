frappe.ui.form.on("Patient", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Check Duplicates"),
				() => _run_duplicate_check(frm, /* show_no_match */ true),
				__("Actions")
			);
			_add_payer_profile_buttons(frm);
		}
		_set_default_payer_profile_filter(frm);
	},

	mobile(frm) {
		_debounced_duplicate_check(frm);
	},

	custom_aadhaar_number(frm) {
		_client_validate_aadhaar(frm);
		_debounced_duplicate_check(frm);
	},

	custom_pan_number(frm) {
		_client_validate_pan(frm);
	},

	custom_abha_number(frm) {
		_client_validate_abha(frm);
	},

	custom_consent_collected(frm) {
		if (frm.doc.custom_consent_collected && !frm.doc.custom_consent_datetime) {
			frm.set_value("custom_consent_datetime", frappe.datetime.now_datetime());
		} else if (!frm.doc.custom_consent_collected) {
			frm.set_value("custom_consent_datetime", null);
		}
	},

	before_save(frm) {
		if (frm.__duplicate_check_acknowledged) {
			frm.__duplicate_check_acknowledged = false;
			return;
		}
		return _run_duplicate_check_before_save(frm);
	},
});

// ---------------------------------------------------------------------------
// Duplicate detection
// ---------------------------------------------------------------------------

let _debounce_timer = null;

function _debounced_duplicate_check(frm) {
	clearTimeout(_debounce_timer);
	_debounce_timer = setTimeout(() => _run_duplicate_check(frm), 600);
}

function _run_duplicate_check(frm, show_no_match = false) {
	const args = _build_duplicate_args(frm);
	if (!args) return;

	frappe.call({
		method: "alcura_ipd_ext.api.patient.check_patient_duplicates",
		args: args,
		callback(r) {
			if (r.message && r.message.length) {
				_show_duplicate_dialog(frm, r.message);
			} else if (show_no_match) {
				frappe.msgprint(__("No duplicate patients found."));
			}
		},
	});
}

function _run_duplicate_check_before_save(frm) {
	const args = _build_duplicate_args(frm);
	if (!args) return;

	return new Promise((resolve, reject) => {
		frappe.call({
			method: "alcura_ipd_ext.api.patient.check_patient_duplicates",
			args: args,
			async: false,
			callback(r) {
				if (r.message && r.message.length) {
					_show_duplicate_dialog(frm, r.message, resolve, reject);
				} else {
					resolve();
				}
			},
			error() {
				resolve();
			},
		});
	});
}

function _build_duplicate_args(frm) {
	const mobile = frm.doc.mobile;
	const aadhaar = frm.doc.custom_aadhaar_number;
	const abha = frm.doc.custom_abha_number;
	const mr_number = frm.doc.custom_mr_number;
	const first_name = frm.doc.first_name;
	const dob = frm.doc.dob;

	if (!mobile && !aadhaar && !abha && !mr_number && !(first_name && dob)) {
		return null;
	}

	return {
		mobile: mobile || "",
		aadhaar: aadhaar || "",
		abha: abha || "",
		mr_number: mr_number || "",
		first_name: first_name || "",
		dob: dob || "",
		exclude_patient: frm.doc.name && !frm.is_new() ? frm.doc.name : "",
	};
}

function _show_duplicate_dialog(frm, matches, resolve, reject) {
	let html = `<p class="text-muted">${__("The following patients may be duplicates:")}</p>`;
	html += '<table class="table table-bordered table-sm">';
	html += `<thead><tr>
		<th>${__("Patient")}</th>
		<th>${__("Name")}</th>
		<th>${__("Mobile")}</th>
		<th>${__("DOB")}</th>
		<th>${__("Match Reasons")}</th>
	</tr></thead><tbody>`;

	for (const m of matches) {
		const link = `<a href="/app/patient/${m.patient}" target="_blank">${m.patient}</a>`;
		const reasons = (m.match_reasons || []).join(", ");
		html += `<tr>
			<td>${link}</td>
			<td>${m.patient_name || ""}</td>
			<td>${m.mobile || ""}</td>
			<td>${m.dob || ""}</td>
			<td>${reasons}</td>
		</tr>`;
	}
	html += "</tbody></table>";

	const is_before_save = !!resolve;

	const d = new frappe.ui.Dialog({
		title: __("Possible Duplicate Patients Found"),
		size: "large",
		fields: [{ fieldtype: "HTML", options: html }],
		primary_action_label: is_before_save ? __("Save Anyway") : __("OK"),
		primary_action() {
			d.hide();
			if (is_before_save) {
				frm.__duplicate_check_acknowledged = true;
				frm.save();
			}
		},
		secondary_action_label: is_before_save ? __("Cancel") : null,
		secondary_action() {
			d.hide();
		},
	});

	d.show();

	if (is_before_save && reject) {
		reject();
	}
}

// ---------------------------------------------------------------------------
// Client-side validation hints (non-blocking)
// ---------------------------------------------------------------------------

function _client_validate_aadhaar(frm) {
	const val = frm.doc.custom_aadhaar_number;
	if (!val) return;
	const cleaned = val.replace(/[\s-]/g, "");
	if (cleaned.length && (cleaned.length !== 12 || !/^\d{12}$/.test(cleaned))) {
		frm.set_df_property(
			"custom_aadhaar_number",
			"description",
			'<span class="text-danger">' + __("Aadhaar must be 12 digits") + "</span>"
		);
	} else {
		frm.set_df_property("custom_aadhaar_number", "description", "");
	}
}

function _client_validate_pan(frm) {
	const val = frm.doc.custom_pan_number;
	if (!val) return;
	const cleaned = val.trim().toUpperCase();
	if (!/^[A-Z]{5}\d{4}[A-Z]$/.test(cleaned)) {
		frm.set_df_property(
			"custom_pan_number",
			"description",
			'<span class="text-danger">' + __("PAN must be in AAAAA9999A format") + "</span>"
		);
	} else {
		frm.set_df_property("custom_pan_number", "description", "");
	}
}

function _client_validate_abha(frm) {
	const val = frm.doc.custom_abha_number;
	if (!val) return;
	const cleaned = val.replace(/[\s-]/g, "");
	if (cleaned.length && (cleaned.length !== 14 || !/^\d{14}$/.test(cleaned))) {
		frm.set_df_property(
			"custom_abha_number",
			"description",
			'<span class="text-danger">' + __("ABHA number must be 14 digits") + "</span>"
		);
	} else {
		frm.set_df_property("custom_abha_number", "description", "");
	}
}

// ---------------------------------------------------------------------------
// Payer Profile integration
// ---------------------------------------------------------------------------

function _add_payer_profile_buttons(frm) {
	frm.add_custom_button(
		__("View Payer Profiles"),
		() => {
			frappe.set_route("List", "Patient Payer Profile", {
				patient: frm.doc.name,
			});
		},
		__("Actions")
	);

	frm.add_custom_button(
		__("Add Payer Profile"),
		() => {
			frappe.new_doc("Patient Payer Profile", {
				patient: frm.doc.name,
			});
		},
		__("Actions")
	);
}

function _set_default_payer_profile_filter(frm) {
	frm.set_query("custom_default_payer_profile", () => ({
		filters: {
			patient: frm.doc.name,
			is_active: 1,
		},
	}));
}
