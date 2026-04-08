// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Lab Sample", {
	refresh(frm) {
		_show_status_indicator(frm);
		_add_action_buttons(frm);
	},

	clinical_order(frm) {
		if (frm.doc.clinical_order) {
			frappe.db.get_value(
				"IPD Clinical Order",
				frm.doc.clinical_order,
				["lab_test_name", "sample_type", "is_fasting_required", "patient", "inpatient_record"],
				(r) => {
					if (r) {
						frm.set_value("lab_test_name", r.lab_test_name);
						frm.set_value("sample_type", r.sample_type);
						frm.set_value("is_fasting_sample", r.is_fasting_required);
						frm.set_value("patient", r.patient);
						frm.set_value("inpatient_record", r.inpatient_record);
					}
				}
			);
		}
	},
});

function _show_status_indicator(frm) {
	if (frm.doc.is_critical_result) {
		if (frm.doc.critical_result_acknowledged_by) {
			frm.dashboard.add_comment(
				__("Critical result acknowledged by {0}", [frm.doc.critical_result_acknowledged_by]),
				"green",
				true
			);
		} else {
			frm.dashboard.add_comment(
				__("CRITICAL RESULT — acknowledgment required"),
				"red",
				true
			);
		}
	}

	if (frm.doc.collection_status === "Recollection Needed") {
		frm.dashboard.add_comment(
			__("Recollection needed: {0}", [frm.doc.recollection_reason || ""]),
			"orange",
			true
		);
	}
}

function _add_action_buttons(frm) {
	if (frm.is_new() || frm.is_dirty()) return;

	const status = frm.doc.status;

	if (status === "Pending") {
		frm.add_custom_button(__("Record Collection"), () => {
			_record_collection(frm);
		}, __("Actions"));
		frm.change_custom_button_type(__("Record Collection"), __("Actions"), "primary");
	}

	if (status === "Collected") {
		frm.add_custom_button(__("Hand Off"), () => {
			_record_handoff(frm);
		}, __("Actions"));
	}

	if (status === "In Transit" || status === "Collected") {
		frm.add_custom_button(__("Receive in Lab"), () => {
			_record_receipt(frm);
		}, __("Actions"));
	}

	if (frm.doc.is_critical_result && !frm.doc.critical_result_acknowledged_by) {
		frm.add_custom_button(__("Acknowledge Critical Result"), () => {
			frappe.call({
				method: "alcura_ipd_ext.api.lab_sample.acknowledge_critical_result",
				args: { sample_name: frm.doc.name },
				freeze: true,
				callback() { frm.reload_doc(); },
			});
		}, __("Actions"));
	}
}

function _record_collection(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Record Sample Collection"),
		fields: [
			{ fieldtype: "Data", fieldname: "collection_site", label: __("Collection Site") },
			{ fieldtype: "Small Text", fieldname: "notes", label: __("Notes") },
		],
		primary_action_label: __("Collect"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.lab_sample.record_collection",
				args: {
					sample_name: frm.doc.name,
					collection_site: values.collection_site || "",
					notes: values.notes || "",
				},
				freeze: true,
				callback() { frm.reload_doc(); },
			});
		},
	});
	d.show();
}

function _record_handoff(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Hand Off Sample"),
		fields: [
			{
				fieldtype: "Select", fieldname: "transport_mode", label: __("Transport Mode"),
				options: "\nManual\nPneumatic Tube\nRunner",
			},
		],
		primary_action_label: __("Hand Off"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.lab_sample.record_handoff",
				args: {
					sample_name: frm.doc.name,
					transport_mode: values.transport_mode || "Manual",
				},
				freeze: true,
				callback() { frm.reload_doc(); },
			});
		},
	});
	d.show();
}

function _record_receipt(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Receive Sample in Lab"),
		fields: [
			{
				fieldtype: "Select", fieldname: "sample_condition", label: __("Sample Condition"),
				options: "Acceptable\nHemolyzed\nClotted\nInsufficient\nContaminated", reqd: 1,
			},
		],
		primary_action_label: __("Receive"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.lab_sample.record_receipt",
				args: {
					sample_name: frm.doc.name,
					sample_condition: values.sample_condition,
				},
				freeze: true,
				callback() { frm.reload_doc(); },
			});
		},
	});
	d.show();
}
