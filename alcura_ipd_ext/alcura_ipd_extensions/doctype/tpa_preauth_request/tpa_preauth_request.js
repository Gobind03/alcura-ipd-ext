frappe.ui.form.on("TPA Preauth Request", {
	setup(frm) {
		frm.set_query("patient_payer_profile", () => ({
			filters: {
				patient: frm.doc.patient || undefined,
				is_active: 1,
				payer_type: ["!=", "Cash"],
			},
		}));
		frm.set_query("inpatient_record", () => ({
			filters: { patient: frm.doc.patient || undefined },
		}));
		frm.set_query("treating_practitioner", () => ({
			filters: { status: "Active" },
		}));
		frm.set_query("room_type_requested", () => ({
			filters: { inpatient_occupancy: 1 },
		}));
	},

	refresh(frm) {
		_set_status_indicator(frm);
		_add_action_buttons(frm);
	},

	patient(frm) {
		if (!frm.doc.patient) return;
		frm.set_query("patient_payer_profile", () => ({
			filters: {
				patient: frm.doc.patient,
				is_active: 1,
				payer_type: ["!=", "Cash"],
			},
		}));
	},
});

function _set_status_indicator(frm) {
	const indicator_map = {
		Draft: "grey",
		Submitted: "blue",
		"Query Raised": "orange",
		Resubmitted: "blue",
		Approved: "green",
		"Partially Approved": "cyan",
		Rejected: "red",
		Closed: "darkgrey",
	};
	const color = indicator_map[frm.doc.status] || "grey";
	frm.page.set_indicator(frm.doc.status, color);
}

function _add_action_buttons(frm) {
	if (frm.is_new()) return;

	const status = frm.doc.status;

	if (status === "Draft") {
		frm.add_custom_button(__("Submit Request"), () => {
			frm.call("action_submit_request").then(() => frm.reload_doc());
		}, __("Actions"));
	}

	if (status === "Submitted" || status === "Resubmitted") {
		frm.add_custom_button(__("Raise Query"), () => {
			frm.call("action_raise_query").then(() => frm.reload_doc());
		}, __("Actions"));

		frm.add_custom_button(__("Approve"), () => {
			_prompt_approved_amount(frm, (amt) => {
				frm.call("action_approve", { approved_amount: amt })
					.then(() => frm.reload_doc());
			});
		}, __("Actions"));

		frm.add_custom_button(__("Partially Approve"), () => {
			_prompt_approved_amount(frm, (amt) => {
				frm.call("action_partially_approve", { approved_amount: amt })
					.then(() => frm.reload_doc());
			});
		}, __("Actions"));

		frm.add_custom_button(__("Reject"), () => {
			frappe.confirm(
				__("Are you sure you want to reject this pre-auth request?"),
				() => frm.call("action_reject").then(() => frm.reload_doc())
			);
		}, __("Actions"));
	}

	if (status === "Query Raised") {
		frm.add_custom_button(__("Resubmit"), () => {
			frm.call("action_resubmit").then(() => frm.reload_doc());
		}, __("Actions"));
	}

	if (["Approved", "Partially Approved", "Rejected"].includes(status)) {
		frm.add_custom_button(__("Close"), () => {
			frm.call("action_close").then(() => frm.reload_doc());
		}, __("Actions"));
	}
}

function _prompt_approved_amount(frm, callback) {
	frappe.prompt(
		{
			fieldname: "approved_amount",
			fieldtype: "Currency",
			label: __("Approved Amount"),
			reqd: 1,
			default: frm.doc.requested_amount,
		},
		(values) => callback(values.approved_amount),
		__("Enter Approved Amount"),
		__("Confirm")
	);
}
