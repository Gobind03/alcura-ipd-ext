// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Bedside Chart", {
	refresh(frm) {
		if (frm.is_new() || frm.is_dirty()) return;

		_show_overdue_banner(frm);
		_add_action_buttons(frm);
	},
});

function _show_overdue_banner(frm) {
	if (frm.doc.status !== "Active") return;
	if (!frm.doc.frequency_minutes) return;

	const last = frm.doc.last_entry_at || frm.doc.started_at;
	if (!last) return;

	const next_due = frappe.datetime.add(last, { minutes: frm.doc.frequency_minutes });
	const now = frappe.datetime.now_datetime();

	if (now > next_due) {
		const overdue_min = Math.floor(
			(new Date(now) - new Date(next_due)) / 60000
		);
		frm.dashboard.add_comment(
			__("Chart is OVERDUE by {0} minutes. Next entry was due at {1}.", [
				overdue_min,
				frappe.datetime.str_to_user(next_due),
			]),
			"red",
			true
		);
	} else {
		frm.dashboard.add_comment(
			__("Next entry due at {0}.", [frappe.datetime.str_to_user(next_due)]),
			"blue",
			true
		);
	}
}

function _add_action_buttons(frm) {
	if (frm.doc.status === "Active") {
		frm.add_custom_button(__("Record Entry"), () => {
			frappe.new_doc("IPD Chart Entry", {
				bedside_chart: frm.doc.name,
				patient: frm.doc.patient,
				inpatient_record: frm.doc.inpatient_record,
				chart_type: frm.doc.chart_type,
			});
		}, __("Actions"));
		frm.change_custom_button_type(__("Record Entry"), __("Actions"), "primary");

		frm.add_custom_button(__("Pause"), () => {
			frm.set_value("status", "Paused");
			frm.save();
		}, __("Actions"));

		frm.add_custom_button(__("Discontinue"), () => {
			frappe.confirm(
				__("Are you sure you want to discontinue this chart?"),
				() => {
					frm.set_value("status", "Discontinued");
					frm.save();
				}
			);
		}, __("Actions"));
	}

	if (frm.doc.status === "Paused") {
		frm.add_custom_button(__("Resume"), () => {
			frm.set_value("status", "Active");
			frm.save();
		}, __("Actions"));
		frm.change_custom_button_type(__("Resume"), __("Actions"), "primary");
	}

	if (frm.doc.total_entries > 0) {
		frm.add_custom_button(__("View Entries"), () => {
			frappe.set_route("List", "IPD Chart Entry", {
				bedside_chart: frm.doc.name,
			});
		}, __("Actions"));
	}
}
