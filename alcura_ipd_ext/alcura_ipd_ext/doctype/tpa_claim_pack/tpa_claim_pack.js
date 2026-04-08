frappe.ui.form.on("TPA Claim Pack", {
	setup(frm) {
		frm.set_query("inpatient_record", () => ({}));
		frm.set_query("tpa_preauth_request", () => ({
			filters: { inpatient_record: frm.doc.inpatient_record || undefined },
		}));
		frm.set_query("final_invoice", () => ({
			filters: { docstatus: 1 },
		}));
	},

	refresh(frm) {
		_set_indicator(frm);
		if (frm.is_new()) return;

		frm.add_custom_button(__("Refresh Availability"), () => {
			frm.call("refresh_document_availability").then(() => frm.reload_doc());
		});

		_add_status_buttons(frm);
	},
});

function _set_indicator(frm) {
	const map = {
		Draft: "grey",
		"In Review": "blue",
		Submitted: "orange",
		Acknowledged: "cyan",
		Settled: "green",
		Disputed: "red",
	};
	frm.page.set_indicator(frm.doc.status, map[frm.doc.status] || "grey");
}

function _add_status_buttons(frm) {
	const status = frm.doc.status;

	if (status === "Draft") {
		frm.add_custom_button(__("Send for Review"), () => {
			frm.call("action_send_for_review").then(() => frm.reload_doc());
		}, __("Actions"));
	}

	if (status === "In Review") {
		frm.add_custom_button(__("Mark Submitted"), () => {
			frm.call("action_mark_submitted").then(() => frm.reload_doc());
		}, __("Actions"));
	}

	if (status === "Submitted") {
		frm.add_custom_button(__("Mark Acknowledged"), () => {
			frm.call("action_mark_acknowledged").then(() => frm.reload_doc());
		}, __("Actions"));

		frm.add_custom_button(__("Mark Disputed"), () => {
			frappe.prompt(
				[
					{ fieldname: "amount", fieldtype: "Currency", label: __("Disallowance Amount") },
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
				],
				(values) => {
					frm.call("action_mark_disputed", {
						disallowance_amount: values.amount,
						reason: values.reason,
					}).then(() => frm.reload_doc());
				},
				__("Dispute Details")
			);
		}, __("Actions"));
	}

	if (status === "Acknowledged") {
		frm.add_custom_button(__("Mark Settled"), () => {
			frappe.prompt(
				[
					{ fieldname: "amount", fieldtype: "Currency", label: __("Settlement Amount"), reqd: 1 },
					{ fieldname: "reference", fieldtype: "Data", label: __("Settlement Reference") },
				],
				(values) => {
					frm.call("action_mark_settled", {
						settlement_amount: values.amount,
						settlement_reference: values.reference,
					}).then(() => frm.reload_doc());
				},
				__("Settlement Details")
			);
		}, __("Actions"));
	}

	if (status === "Disputed") {
		frm.add_custom_button(__("Resubmit"), () => {
			frm.call("action_mark_submitted").then(() => frm.reload_doc());
		}, __("Actions"));
	}
}
