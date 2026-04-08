// Client-side customisation for Healthcare Service Unit Type form.
// Loaded via doctype_js hook in hooks.py.

const CRITICAL_CARE_CATEGORIES = new Set([
	"ICU", "CICU", "MICU", "NICU", "PICU", "SICU", "HDU", "Burns",
]);

const IPD_FIELDS = [
	"ipd_room_category",
	"occupancy_class",
	"nursing_intensity",
	"is_critical_care_unit",
	"supports_isolation",
	"package_eligible",
	"default_price_list",
];

frappe.ui.form.on("Healthcare Service Unit Type", {
	setup(frm) {
		frm.set_query("default_price_list", () => ({
			filters: { selling: 1 },
		}));
	},

	ipd_room_category(frm) {
		const cat = frm.doc.ipd_room_category;
		const is_cc = CRITICAL_CARE_CATEGORIES.has(cat) ? 1 : 0;
		frm.set_value("is_critical_care_unit", is_cc);

		if (cat === "Isolation") {
			frm.set_value("supports_isolation", 1);
		}

		if (is_cc && !frm.doc.nursing_intensity) {
			frm.set_value("nursing_intensity", "Critical");
		}
	},

	inpatient_occupancy(frm) {
		if (!frm.doc.inpatient_occupancy) {
			_clear_ipd_fields(frm);
		}
	},
});

function _clear_ipd_fields(frm) {
	IPD_FIELDS.forEach((field) => {
		const meta = frappe.meta.get_docfield(frm.doctype, field);
		if (!meta) return;

		const blank = meta.fieldtype === "Check" ? 0 : "";
		if (frm.doc[field] !== blank) {
			frm.set_value(field, blank);
		}
	});
}
