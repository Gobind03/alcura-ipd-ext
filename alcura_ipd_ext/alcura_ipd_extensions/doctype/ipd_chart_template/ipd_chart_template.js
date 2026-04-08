// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Chart Template", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Preview Parameters"), () => {
				const rows = (frm.doc.parameters || []).sort(
					(a, b) => (a.display_order || 0) - (b.display_order || 0)
				);
				if (!rows.length) {
					frappe.msgprint(__("No parameters defined."));
					return;
				}
				const html = rows
					.map(
						(r) =>
							`<tr>
								<td>${r.parameter_name}</td>
								<td>${r.parameter_type}</td>
								<td>${r.uom || "-"}</td>
								<td>${r.is_mandatory ? "Yes" : "No"}</td>
								<td>${r.min_value || "-"} – ${r.max_value || "-"}</td>
								<td>${r.critical_low || "-"} – ${r.critical_high || "-"}</td>
							</tr>`
					)
					.join("");

				frappe.msgprint({
					title: __("Chart Parameters"),
					message: `<table class="table table-bordered table-sm">
						<thead><tr>
							<th>${__("Parameter")}</th>
							<th>${__("Type")}</th>
							<th>${__("UOM")}</th>
							<th>${__("Required")}</th>
							<th>${__("Range")}</th>
							<th>${__("Critical")}</th>
						</tr></thead>
						<tbody>${html}</tbody>
					</table>`,
					wide: true,
				});
			});
		}
	},
});
