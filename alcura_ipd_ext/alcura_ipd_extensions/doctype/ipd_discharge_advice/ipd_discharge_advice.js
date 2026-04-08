// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Discharge Advice", {
	refresh(frm) {
		_set_indicator(frm);

		if (frm.is_new() || frm.is_dirty()) return;

		if (frm.doc.status === "Draft") {
			frm.add_custom_button(__("Submit Advice"), () => {
				frappe.confirm(
					__("Submit this discharge advice? Downstream departments will be notified."),
					() => {
						frm.call("submit_advice").then(() => frm.reload_doc());
					}
				);
			});
			frm.change_custom_button_type(__("Submit Advice"), null, "primary");

			frm.add_custom_button(__("Cancel"), () => {
				_prompt_cancel(frm);
			});
		}

		if (frm.doc.status === "Advised") {
			frm.add_custom_button(__("Acknowledge"), () => {
				frm.call("acknowledge").then(() => frm.reload_doc());
			});
			frm.change_custom_button_type(__("Acknowledge"), null, "primary");

			frm.add_custom_button(__("Cancel"), () => {
				_prompt_cancel(frm);
			});
		}

		if (frm.doc.status === "Acknowledged") {
			frm.add_custom_button(__("Mark Completed"), () => {
				frappe.confirm(
					__("Mark this discharge as completed?"),
					() => {
						frm.call("complete").then(() => frm.reload_doc());
					}
				);
			});
			frm.change_custom_button_type(__("Mark Completed"), null, "primary");
		}
	},

	inpatient_record(frm) {
		if (frm.doc.inpatient_record) {
			frappe.db.get_value(
				"Inpatient Record",
				frm.doc.inpatient_record,
				["patient", "company", "primary_practitioner"],
				(r) => {
					if (r) {
						frm.set_value("patient", r.patient);
						frm.set_value("company", r.company);
						if (!frm.doc.consultant && r.primary_practitioner) {
							frm.set_value("consultant", r.primary_practitioner);
						}
					}
				}
			);
		}
	},
});

function _set_indicator(frm) {
	const map = {
		Draft: "orange",
		Advised: "blue",
		Acknowledged: "cyan",
		Completed: "green",
		Cancelled: "red",
	};
	const color = map[frm.doc.status] || "grey";
	frm.page.set_indicator(__(frm.doc.status), color);
}

function _prompt_cancel(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Cancel Discharge Advice"),
		fields: [
			{
				fieldtype: "Small Text",
				fieldname: "reason",
				label: __("Cancellation Reason"),
				reqd: 1,
			},
		],
		primary_action_label: __("Cancel Advice"),
		primary_action(values) {
			d.hide();
			frm.call("cancel_advice", { reason: values.reason }).then(() =>
				frm.reload_doc()
			);
		},
	});
	d.show();
}
