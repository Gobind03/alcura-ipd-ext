frappe.ui.form.on("Room Tariff Mapping", {
	setup(frm) {
		frm.set_query("room_type", () => ({
			filters: { inpatient_occupancy: 1 },
		}));

		frm.set_query("price_list", () => ({
			filters: { selling: 1 },
		}));

		frm.set_query("payer", () => ({
			filters: { disabled: 0 },
		}));

		frm.set_query("item_code", "tariff_items", () => ({
			filters: { disabled: 0 },
		}));
	},

	room_type(frm) {
		if (!frm.doc.room_type) {
			return;
		}
		frappe.db.get_value(
			"Healthcare Service Unit Type",
			frm.doc.room_type,
			"default_price_list",
			(r) => {
				if (r && r.default_price_list && !frm.doc.price_list) {
					frm.set_value("price_list", r.default_price_list);
				}
			}
		);
	},

	payer_type(frm) {
		if (frm.doc.payer_type === "Cash") {
			frm.set_value("payer", "");
		}
	},
});
