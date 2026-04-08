// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Clinical Order", {
	refresh(frm) {
		_set_dynamic_labels(frm);
		_add_action_buttons(frm);
		_show_sla_indicator(frm);
	},

	order_type(frm) {
		_set_dynamic_labels(frm);
	},

	is_stat(frm) {
		if (frm.doc.is_stat && frm.doc.urgency !== "STAT" && frm.doc.urgency !== "Emergency") {
			frm.set_value("urgency", "STAT");
		}
	},

	medication_item(frm) {
		if (frm.doc.medication_item && !frm.doc.medication_name) {
			frappe.db.get_value("Item", frm.doc.medication_item, "item_name", (r) => {
				if (r && r.item_name) {
					frm.set_value("medication_name", r.item_name);
				}
			});
		}
	},

	lab_test_template(frm) {
		if (frm.doc.lab_test_template && !frm.doc.lab_test_name) {
			frappe.db.get_value("Lab Test Template", frm.doc.lab_test_template, "lab_test_name", (r) => {
				if (r && r.lab_test_name) {
					frm.set_value("lab_test_name", r.lab_test_name);
				}
			});
		}
	},
});

function _set_dynamic_labels(frm) {
	const type = frm.doc.order_type;
	if (!type) return;

	const label_map = {
		Medication: "Medication Order",
		"Lab Test": "Lab Test Order",
		Radiology: "Radiology Order",
		Procedure: "Procedure Order",
	};
	frm.page.set_title(label_map[type] || "Clinical Order");
}

function _add_action_buttons(frm) {
	if (frm.is_new() || frm.is_dirty()) return;

	const status = frm.doc.status;

	if (status === "Draft") {
		frm.add_custom_button(__("Place Order"), () => {
			_transition(frm, "Ordered");
		}, __("Actions"));
		frm.change_custom_button_type(__("Place Order"), __("Actions"), "primary");
	}

	if (status === "Ordered") {
		frm.add_custom_button(__("Acknowledge"), () => {
			_transition(frm, "Acknowledged");
		}, __("Actions"));
		frm.change_custom_button_type(__("Acknowledge"), __("Actions"), "primary");
	}

	if (status === "Acknowledged") {
		frm.add_custom_button(__("Start"), () => {
			_transition(frm, "In Progress");
		}, __("Actions"));
	}

	if (["Acknowledged", "In Progress"].includes(status)) {
		frm.add_custom_button(__("Complete"), () => {
			_transition(frm, "Completed");
		}, __("Actions"));
		frm.change_custom_button_type(__("Complete"), __("Actions"), "primary");
	}

	if (!["Completed", "Cancelled"].includes(status)) {
		frm.add_custom_button(__("Cancel Order"), () => {
			_prompt_cancel(frm);
		}, __("Actions"));

		if (status !== "On Hold") {
			frm.add_custom_button(__("Hold"), () => {
				_prompt_hold(frm);
			}, __("Actions"));
		} else {
			frm.add_custom_button(__("Resume"), () => {
				_transition(frm, "Ordered");
			}, __("Actions"));
		}
	}
}

function _transition(frm, new_status) {
	frappe.call({
		method: "alcura_ipd_ext.api.clinical_order.transition_order",
		args: { order: frm.doc.name, new_status: new_status },
		freeze: true,
		freeze_message: __("Updating order..."),
		callback() {
			frm.reload_doc();
		},
	});
}

function _prompt_cancel(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Cancel Order"),
		fields: [
			{
				fieldtype: "Small Text",
				fieldname: "reason",
				label: __("Cancellation Reason"),
				reqd: 1,
			},
		],
		primary_action_label: __("Cancel Order"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.clinical_order.cancel_order",
				args: { order: frm.doc.name, reason: values.reason },
				freeze: true,
				callback() {
					frm.reload_doc();
				},
			});
		},
	});
	d.show();
}

function _prompt_hold(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Hold Order"),
		fields: [
			{
				fieldtype: "Small Text",
				fieldname: "reason",
				label: __("Hold Reason"),
				reqd: 1,
			},
		],
		primary_action_label: __("Hold"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.clinical_order.hold_order",
				args: { order: frm.doc.name, reason: values.reason },
				freeze: true,
				callback() {
					frm.reload_doc();
				},
			});
		},
	});
	d.show();
}

function _show_sla_indicator(frm) {
	if (!frm.doc.current_sla_target_at) return;

	const target = moment(frm.doc.current_sla_target_at);
	const now = moment();
	const diff_min = target.diff(now, "minutes");

	if (frm.doc.is_sla_breached) {
		frm.dashboard.add_comment(
			__("SLA BREACHED — {0} breach(es) recorded", [frm.doc.sla_breach_count]),
			"red",
			true
		);
	} else if (diff_min < 0) {
		frm.dashboard.add_comment(
			__("SLA overdue by {0} minutes", [Math.abs(diff_min)]),
			"red",
			true
		);
	} else if (diff_min <= 15) {
		frm.dashboard.add_comment(
			__("SLA target in {0} minutes", [diff_min]),
			"orange",
			true
		);
	}
}
