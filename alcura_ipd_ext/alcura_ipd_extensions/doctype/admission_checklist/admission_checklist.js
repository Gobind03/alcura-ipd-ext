// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-D2: Admission Checklist form — provides action buttons per row
// to complete or waive individual checklist items.

frappe.ui.form.on("Admission Checklist", {
	refresh(frm) {
		if (frm.is_new() || frm.is_dirty()) return;
		if (frm.doc.status === "Complete" || frm.doc.status === "Overridden") return;

		_add_complete_all_button(frm);
		_render_item_actions(frm);
	},
});

function _add_complete_all_button(frm) {
	const pending = (frm.doc.checklist_entries || []).filter(
		(e) => e.status === "Pending"
	);
	if (!pending.length) return;

	frm.add_custom_button(__("Complete All Pending"), () => {
		frappe.confirm(
			__("Mark all {0} pending items as Completed?", [pending.length]),
			() => {
				const promises = pending.map((row) =>
					frappe.call({
						method: "alcura_ipd_ext.api.admission.complete_checklist_item",
						args: { checklist: frm.doc.name, row_idx: row.idx },
					})
				);
				Promise.all(promises).then(() => {
					frappe.show_alert({
						message: __("All pending items completed."),
						indicator: "green",
					});
					frm.reload_doc();
				});
			}
		);
	}, __("Actions"));
}

function _render_item_actions(frm) {
	const grid = frm.fields_dict.checklist_entries.grid;

	for (const row of frm.doc.checklist_entries || []) {
		if (row.status !== "Pending") continue;

		const grid_row = grid.grid_rows_by_docname[row.name];
		if (!grid_row || !grid_row.wrapper) continue;

		const $actions = $('<div class="checklist-actions" style="margin-top: 4px;"></div>');

		const $complete = $(
			`<button class="btn btn-xs btn-success mr-1">${__("Complete")}</button>`
		);
		$complete.on("click", () => {
			frappe.call({
				method: "alcura_ipd_ext.api.admission.complete_checklist_item",
				args: { checklist: frm.doc.name, row_idx: row.idx },
				callback() {
					frm.reload_doc();
				},
			});
		});
		$actions.append($complete);

		if (frappe.user_roles.includes("Healthcare Administrator")) {
			const $waive = $(
				`<button class="btn btn-xs btn-warning">${__("Waive")}</button>`
			);
			$waive.on("click", () => {
				_prompt_waive_reason(frm, row);
			});
			$actions.append($waive);
		}

		grid_row.wrapper
			.find(".row-index, .static-area")
			.first()
			.closest("div")
			.append($actions);
	}
}

function _prompt_waive_reason(frm, row) {
	const d = new frappe.ui.Dialog({
		title: __("Waive: {0}", [row.item_label]),
		fields: [
			{
				fieldtype: "Small Text",
				fieldname: "reason",
				label: __("Reason for Waiving"),
				reqd: 1,
			},
		],
		primary_action_label: __("Waive Item"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.admission.waive_checklist_item",
				args: {
					checklist: frm.doc.name,
					row_idx: row.idx,
					reason: values.reason,
				},
				callback() {
					frm.reload_doc();
				},
			});
		},
	});
	d.show();
}
