frappe.ui.form.on("Discharge Billing Checklist", {
	setup(frm) {
		frm.set_query("inpatient_record", () => ({
			filters: { status: ["not in", ["Discharged"]] },
		}));
	},

	refresh(frm) {
		_set_indicator(frm);
		if (frm.is_new()) return;

		frm.add_custom_button(__("Refresh Auto-Checks"), () => {
			frm.call("refresh_auto_checks").then(() => frm.reload_doc());
		});

		if (frm.doc.status === "Pending" || frm.doc.status === "In Progress") {
			frm.add_custom_button(__("Override All"), () => {
				frappe.prompt(
					{
						fieldname: "reason",
						fieldtype: "Small Text",
						label: __("Override Reason"),
						reqd: 1,
					},
					(values) => {
						frm.call("authorize_override", { reason: values.reason })
							.then(() => frm.reload_doc());
					},
					__("Override Discharge Checklist"),
					__("Authorize Override")
				);
			}, __("Actions"));
		}
	},
});

frappe.ui.form.on("Discharge Checklist Item", {
	check_status(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.check_status === "Waived" && !row.waiver_reason) {
			frappe.prompt(
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Waiver Reason"),
					reqd: 1,
				},
				(values) => {
					frappe.model.set_value(cdt, cdn, "waiver_reason", values.reason);
				},
				__("Waiver Reason Required")
			);
		}
	},
});

function _set_indicator(frm) {
	const map = {
		Pending: "orange",
		"In Progress": "blue",
		Cleared: "green",
		Overridden: "yellow",
	};
	frm.page.set_indicator(frm.doc.status, map[frm.doc.status] || "grey");
}
