// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-E2: Nursing Risk Summary report filters

frappe.query_reports["Nursing Risk Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
		},
		{
			fieldname: "risk_type",
			label: __("Risk Type"),
			fieldtype: "Select",
			options: "\nFall Risk\nPressure Injury\nNutrition\nAllergy",
		},
		{
			fieldname: "risk_level",
			label: __("Minimum Risk Level"),
			fieldtype: "Select",
			options: "\nHigh\nModerate\nLow",
			description: __("Show patients at or above this risk level"),
		},
		{
			fieldname: "consultant",
			label: __("Consultant"),
			fieldtype: "Link",
			options: "Healthcare Practitioner",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "fall_risk_level") {
			value = _apply_risk_badge(value, { High: "red", Moderate: "orange", Low: "green" });
		}
		if (column.fieldname === "pressure_risk_level") {
			value = _apply_risk_badge(value, {
				"Very High": "red", High: "red", Moderate: "orange", Low: "blue", "No Risk": "green",
			});
		}
		if (column.fieldname === "nutrition_risk_level") {
			value = _apply_risk_badge(value, { High: "red", Medium: "orange", Low: "green" });
		}
		if (column.fieldname === "allergy_alert" && data && data.allergy_alert) {
			value = '<span class="indicator-pill red">ALLERGY</span>';
		}

		return value;
	},
};

function _apply_risk_badge(value, color_map) {
	if (!value) return value;
	const plain = $("<div>").html(value).text().trim();
	const color = color_map[plain] || "grey";
	return `<span class="indicator-pill ${color}">${plain}</span>`;
}
