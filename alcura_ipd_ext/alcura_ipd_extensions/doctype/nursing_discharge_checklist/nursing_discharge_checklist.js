// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nursing Discharge Checklist", {
	refresh(frm) {
		_set_indicator(frm);
		_show_progress_banner(frm);

		if (frm.is_new() || frm.is_dirty()) return;

		if (frm.doc.status !== "Completed") {
			frm.add_custom_button(__("Complete & Sign Off"), () => {
				_prompt_signoff(frm);
			});
			frm.change_custom_button_type(__("Complete & Sign Off"), null, "primary");
		}

		if (frm.doc.status === "Completed" && !frm.doc.verified_by) {
			frm.add_custom_button(__("Verify Handover"), () => {
				frappe.confirm(
					__("Verify this discharge handover?"),
					() => {
						frm.call("verify").then(() => frm.reload_doc());
					}
				);
			});
			frm.change_custom_button_type(__("Verify Handover"), null, "primary");
		}
	},
});

frappe.ui.form.on("Nursing Discharge Checklist Item", {
	item_status(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.item_status === "Skipped" && !row.skip_reason) {
			const d = new frappe.ui.Dialog({
				title: __("Skip Reason"),
				fields: [
					{
						fieldtype: "Small Text",
						fieldname: "reason",
						label: __("Reason for Skipping"),
						reqd: 1,
					},
				],
				primary_action_label: __("Skip"),
				primary_action(values) {
					d.hide();
					frm.call("skip_item", {
						item_idx: row.idx,
						reason: values.reason,
					}).then(() => frm.reload_doc());
				},
			});
			d.show();
			return;
		}

		if (row.item_status === "Done") {
			frm.call("complete_item", { item_idx: row.idx }).then(() =>
				frm.reload_doc()
			);
		} else if (row.item_status === "Not Applicable") {
			frm.call("mark_not_applicable", { item_idx: row.idx }).then(() =>
				frm.reload_doc()
			);
		}
	},
});

function _set_indicator(frm) {
	const map = {
		Pending: "orange",
		"In Progress": "blue",
		Completed: "green",
	};
	const color = map[frm.doc.status] || "grey";
	frm.page.set_indicator(__(frm.doc.status), color);
}

function _show_progress_banner(frm) {
	const total = frm.doc.total_items || 0;
	const done = frm.doc.completed_items || 0;
	if (!total) return;

	const pct = Math.round((done / total) * 100);
	const color = pct === 100 ? "green" : pct > 50 ? "blue" : "orange";

	frm.dashboard.add_comment(
		`<strong>${__("Progress")}:</strong> ${done}/${total} items (${pct}%)`,
		color,
		true
	);

	if (frm.doc.verified_by) {
		frm.dashboard.add_comment(
			`<strong>${__("Verified by")}:</strong> ${frm.doc.verified_by} on ${frappe.datetime.str_to_user(frm.doc.verified_on)}`,
			"green",
			true
		);
	}
}

function _prompt_signoff(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Complete & Sign Off"),
		fields: [
			{
				fieldtype: "Text Editor",
				fieldname: "handover_notes",
				label: __("Handover Notes"),
				description: __("Any additional notes for the discharge desk"),
			},
		],
		primary_action_label: __("Sign Off"),
		primary_action(values) {
			d.hide();
			frm.call("sign_off", {
				handover_notes: values.handover_notes || "",
			}).then(() => frm.reload_doc());
		},
	});
	d.show();
}
