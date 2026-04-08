app_name = "alcura_ipd_ext"
app_title = "Alcura IPD Extensions"
app_publisher = "Alcura"
app_description = "Alcura IPD Extensions for Frappe/ERPNext Healthcare"
app_email = "dev@alcura.io"
app_license = "MIT"
app_version = "0.0.1"

# ---------------------------------------------------------------------------
# App Includes (used to inject assets into Desk / Portal)
# ---------------------------------------------------------------------------

# app_include_css = "/assets/alcura_ipd_ext/css/alcura_ipd_ext.css"
app_include_js = "/assets/alcura_ipd_ext/js/icu_trend_chart.js"

# web_include_css = "/assets/alcura_ipd_ext/css/alcura_ipd_ext_web.css"
# web_include_js = "/assets/alcura_ipd_ext/js/alcura_ipd_ext_web.js"

# ---------------------------------------------------------------------------
# DocType-specific JS / CSS
# ---------------------------------------------------------------------------

doctype_js = {
	"Healthcare Service Unit Type": "public/js/healthcare_service_unit_type.js",
	"Inpatient Record": "public/js/inpatient_record.js",
	"Patient": "public/js/patient.js",
	"Patient Encounter": "public/js/patient_encounter.js",
	"Patient Assessment": "public/js/patient_assessment.js",
	"IPD Intake Assessment": "public/js/ipd_intake_assessment.js",
	"IPD Bedside Chart": "public/js/ipd_bedside_chart.js",
}

# doctype_list_js = {"DocType Name": "public/js/doctype_name_list.js"}
# doctype_tree_js = {"DocType Name": "public/js/doctype_name_tree.js"}
# doctype_calendar_js = {"DocType Name": "public/js/doctype_name_calendar.js"}

# webform_include_js = {"Web Form Name": "public/js/web_form.js"}
# webform_include_css = {"Web Form Name": "public/css/web_form.css"}

# ---------------------------------------------------------------------------
# Website / Portal generators
# ---------------------------------------------------------------------------

# website_generators = ["Web Page"]

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

# before_install = "alcura_ipd_ext.setup.install.before_install"
after_install = "alcura_ipd_ext.setup.install.after_install"
before_uninstall = "alcura_ipd_ext.setup.install.before_uninstall"
# after_uninstall = "alcura_ipd_ext.setup.install.after_uninstall"

# ---------------------------------------------------------------------------
# App lifecycle hooks (run per-app on bench install / uninstall)
# ---------------------------------------------------------------------------

# before_app_install = "alcura_ipd_ext.setup.install.before_app_install"
# after_app_install = "alcura_ipd_ext.setup.install.after_app_install"

# ---------------------------------------------------------------------------
# Desk Notifications
# ---------------------------------------------------------------------------

# notification_config = "alcura_ipd_ext.notifications.get_notification_config"

# ---------------------------------------------------------------------------
# Permissions evaluated in scripted ways
# ---------------------------------------------------------------------------

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# ---------------------------------------------------------------------------
# DocType Class overrides
# ---------------------------------------------------------------------------

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo",
# }

# ---------------------------------------------------------------------------
# Dashboard overrides
# ---------------------------------------------------------------------------

override_doctype_dashboards = {
	"Patient": "alcura_ipd_ext.overrides.patient_dashboard.get_dashboard_data",
	"Inpatient Record": "alcura_ipd_ext.overrides.inpatient_record_dashboard.get_dashboard_data",
}

# ---------------------------------------------------------------------------
# Document Events
# ---------------------------------------------------------------------------

doc_events = {
	"Healthcare Service Unit Type": {
		"validate": "alcura_ipd_ext.overrides.healthcare_service_unit_type.validate",
	},
	"Healthcare Service Unit": {
		"on_update": "alcura_ipd_ext.overrides.healthcare_service_unit.on_update",
	},
	"Patient": {
		"validate": "alcura_ipd_ext.overrides.patient.validate",
	},
	"Patient Assessment": {
		"validate": "alcura_ipd_ext.overrides.patient_assessment.validate",
		"on_submit": "alcura_ipd_ext.overrides.patient_assessment.on_submit",
	},
	"Patient Encounter": {
		"validate": "alcura_ipd_ext.overrides.patient_encounter_events.validate",
		"on_submit": "alcura_ipd_ext.overrides.patient_encounter_events.on_submit",
	},
	"Lab Test": {
		"on_submit": "alcura_ipd_ext.overrides.lab_test_events.on_submit",
		"on_cancel": "alcura_ipd_ext.overrides.lab_test_events.on_cancel",
	},
}

# ---------------------------------------------------------------------------
# Scheduled Tasks
# ---------------------------------------------------------------------------

scheduler_events = {
	"cron": {
		"*/5 * * * *": [
			"alcura_ipd_ext.tasks.expire_bed_reservations",
			"alcura_ipd_ext.tasks.check_order_sla_breaches",
		],
		"*/15 * * * *": [
			"alcura_ipd_ext.tasks.check_overdue_charts",
			"alcura_ipd_ext.tasks.mark_overdue_mar_entries",
			"alcura_ipd_ext.tasks.check_protocol_compliance",
			"alcura_ipd_ext.tasks.check_housekeeping_sla_breaches",
		],
	},
	"daily": [
		"alcura_ipd_ext.tasks.notify_expiring_payer_profiles",
	],
}

# ---------------------------------------------------------------------------
# Override Whitelisted Methods
# ---------------------------------------------------------------------------

# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": (
# 		"alcura_ipd_ext.api.events.get_events"
# 	),
# }

# ---------------------------------------------------------------------------
# Jinja customizations
# ---------------------------------------------------------------------------

jinja = {
	"methods": [
		"alcura_ipd_ext.utils.label_helpers.generate_qr_svg",
		"alcura_ipd_ext.utils.label_helpers.generate_barcode_svg",
		"alcura_ipd_ext.utils.label_helpers.format_allergy_markers",
		"alcura_ipd_ext.utils.label_helpers.get_admission_label_context",
	],
}

# ---------------------------------------------------------------------------
# Fixtures (auto-exported / imported on install)
# ---------------------------------------------------------------------------

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Alcura IPD Extensions"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Alcura IPD Extensions"]]},
]

# ---------------------------------------------------------------------------
# User Data Protection
# ---------------------------------------------------------------------------

# user_data_fields = [
# 	{"doctype": "Patient", "filter_by": "email_id", "redact_fields": ["patient_name"], "partial": True},
# ]

# ---------------------------------------------------------------------------
# Authentication and Authorization
# ---------------------------------------------------------------------------

# auth_hooks = [
# 	"alcura_ipd_ext.auth.validate",
# ]
