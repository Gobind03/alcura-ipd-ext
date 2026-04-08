// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bed Housekeeping Task", {
	refresh(frm) {
		_set_indicator(frm);
		_show_sla_banner(frm);

		if (frm.is_new() || frm.is_dirty()) return;

		if (frm.doc.status === "Pending") {
			frm.add_custom_button(__("Start Cleaning"), () => {
				frm.call("start_task").then(() => frm.reload_doc());
			});
			frm.change_custom_button_type(__("Start Cleaning"), null, "primary");

			frm.add_custom_button(__("Cancel Task"), () => {
				frappe.confirm(
					__("Cancel this housekeeping task?"),
					() => frm.call("cancel_task").then(() => frm.reload_doc())
				);
			});
		}

		if (frm.doc.status === "In Progress") {
			frm.add_custom_button(__("Complete Cleaning"), () => {
				frm.call("complete_task").then(() => {
					frappe.show_alert({
						message: __("Bed cleaning completed. Bed is now available."),
						indicator: "green",
					});
					frm.reload_doc();
				});
			});
			frm.change_custom_button_type(__("Complete Cleaning"), null, "primary");

			frm.add_custom_button(__("Cancel Task"), () => {
				frappe.confirm(
					__("Cancel this housekeeping task?"),
					() => frm.call("cancel_task").then(() => frm.reload_doc())
				);
			});
		}
	},
});

function _set_indicator(frm) {
	const map = {
		Pending: "orange",
		"In Progress": "blue",
		Completed: "green",
		Cancelled: "red",
	};
	const color = map[frm.doc.status] || "grey";
	frm.page.set_indicator(__(frm.doc.status), color);
}

function _show_sla_banner(frm) {
	if (!frm.doc.sla_target_minutes || frm.doc.status === "Completed" || frm.doc.status === "Cancelled") {
		return;
	}

	if (frm.doc.sla_breached) {
		frm.dashboard.add_comment(
			__("SLA BREACHED — target was {0} minutes", [frm.doc.sla_target_minutes]),
			"red",
			true
		);
		return;
	}

	const created = moment(frm.doc.created_on);
	const deadline = created.clone().add(frm.doc.sla_target_minutes, "minutes");
	const remaining = deadline.diff(moment(), "minutes");

	if (remaining <= 0) {
		frm.dashboard.add_comment(
			__("SLA BREACHED — cleaning overdue by {0} minutes", [Math.abs(remaining)]),
			"red",
			true
		);
	} else if (remaining <= 15) {
		frm.dashboard.add_comment(
			__("SLA warning — {0} minutes remaining", [remaining]),
			"orange",
			true
		);
	} else {
		frm.dashboard.add_comment(
			__("SLA target: {0} minutes — {1} minutes remaining", [frm.doc.sla_target_minutes, remaining]),
			"blue",
			true
		);
	}

	if (frm.doc.turnaround_minutes && frm.doc.status === "Completed") {
		frm.dashboard.add_comment(
			__("Turnaround: {0} minutes", [frm.doc.turnaround_minutes]),
			"green",
			true
		);
	}
}
