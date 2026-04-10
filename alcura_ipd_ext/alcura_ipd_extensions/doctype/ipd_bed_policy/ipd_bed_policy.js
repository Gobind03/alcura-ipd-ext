// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Bed Policy", {
	refresh(frm) {
		frm.page.set_indicator(__("Settings"), "blue");
		frm.set_intro(
			__(
				"Configure hospital-wide bed operation policies. " +
				"These settings govern availability computation, gender enforcement, " +
				"housekeeping SLAs, and payer eligibility filtering across the IPD module."
			)
		);

		frm.add_custom_button(
			__("Generate Demo Data"),
			() => _confirm_generate_demo(frm),
			__("Demo Data")
		);

		frm.add_custom_button(
			__("Clear Demo Data"),
			() => _confirm_clear_demo(frm),
			__("Demo Data")
		);
	},
});

function _confirm_generate_demo(frm) {
	frappe.confirm(
		__(
			"<b>Generate Demo Data?</b><br><br>" +
			"This will create ~25 demo patients with admissions, clinical orders, " +
			"charting, MAR entries, nursing notes, payer profiles, protocol bundles, " +
			"discharge workflows, and hospital infrastructure (wards, rooms, beds).<br><br>" +
			"The data is designed for realistic reporting and demonstration.<br><br>" +
			"<b>This should only be used on development/demo sites.</b>"
		),
		() => {
			frappe.call({
				method: "alcura_ipd_ext.setup.demo_data.generate_demo_data",
				freeze: true,
				freeze_message: __("Generating demo data — this may take a minute..."),
				callback(r) {
					if (r.message) {
						let summary = r.message.summary || {};
						let details = Object.entries(summary)
							.map(([dt, count]) => `${dt}: <b>${count}</b>`)
							.join("<br>");
						frappe.msgprint({
							title: __("Demo Data Generated"),
							indicator: "green",
							message: `${r.message.message}<br><br>${details}`,
						});
					}
				},
				error() {
					frappe.msgprint({
						title: __("Error"),
						indicator: "red",
						message: __("Failed to generate demo data. Check the Error Log for details."),
					});
				},
			});
		}
	);
}

function _confirm_clear_demo(frm) {
	frappe.confirm(
		__(
			"<b>Clear all demo data?</b><br><br>" +
			"This will permanently delete all records created by the demo data generator, " +
			"including patients, admissions, orders, charts, and hospital infrastructure.<br><br>" +
			"<b>This action cannot be undone.</b>"
		),
		() => {
			frappe.call({
				method: "alcura_ipd_ext.setup.demo_data.clear_demo_data",
				freeze: true,
				freeze_message: __("Clearing demo data..."),
				callback(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Demo Data Cleared"),
							indicator: "green",
							message: r.message.message,
						});
					}
				},
				error(r) {
					let server_msg = "";
					try {
						let msgs = JSON.parse(r.responseText);
						server_msg = (msgs._server_messages || msgs.exc || msgs.message || "");
						if (typeof server_msg === "string" && server_msg.startsWith("["))
							server_msg = JSON.parse(server_msg).join("<br>");
					} catch (_e) {
						server_msg = r.responseText || "";
					}
					frappe.msgprint({
						title: __("Error"),
						indicator: "red",
						message: __("Failed to clear demo data.") + "<br><br><pre>" + server_msg + "</pre>",
					});
				},
			});
		}
	);
}
