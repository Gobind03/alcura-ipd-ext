"""IPD Chart Entry — individual recording for parameter-based charts."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class IPDChartEntry(Document):
	def before_insert(self):
		self.recorded_by = self.recorded_by or frappe.session.user
		self._populate_from_chart()

	def validate(self):
		self._validate_chart_active()
		self._validate_correction()
		self._validate_entry_datetime()
		self._check_critical_observations()

	def after_insert(self):
		self._update_bedside_chart()

	def _populate_from_chart(self):
		if self.bedside_chart:
			chart = frappe.db.get_value(
				"IPD Bedside Chart",
				self.bedside_chart,
				["patient", "inpatient_record", "chart_type"],
				as_dict=True,
			)
			if chart:
				self.patient = self.patient or chart.patient
				self.inpatient_record = self.inpatient_record or chart.inpatient_record
				self.chart_type = chart.chart_type

	def _validate_chart_active(self):
		if not self.bedside_chart:
			return
		status = frappe.db.get_value("IPD Bedside Chart", self.bedside_chart, "status")
		if status in ("Discontinued", "Paused"):
			frappe.throw(
				_("Cannot record entries for a {0} chart.").format(status)
			)

	def _validate_correction(self):
		if self.is_correction:
			if not self.corrects_entry:
				frappe.throw(_("Correction entries must specify which entry they correct."))
			if not (self.correction_reason or "").strip():
				frappe.throw(_("A correction reason is required."))

			original_status = frappe.db.get_value(
				"IPD Chart Entry", self.corrects_entry, "status"
			)
			if original_status == "Corrected":
				frappe.throw(_("The original entry has already been corrected."))

	def _validate_entry_datetime(self):
		if self.entry_datetime:
			tolerance_minutes = 5
			future_limit = frappe.utils.add_to_date(now_datetime(), minutes=tolerance_minutes)
			if get_datetime(self.entry_datetime) > future_limit:
				frappe.throw(_("Entry date/time cannot be in the future."))

	def _check_critical_observations(self):
		if not self.bedside_chart:
			return

		template_name = frappe.db.get_value(
			"IPD Bedside Chart", self.bedside_chart, "chart_template"
		)
		if not template_name:
			return

		params = {
			r.parameter_name: r
			for r in frappe.get_all(
				"IPD Chart Template Parameter",
				filters={"parent": template_name},
				fields=["parameter_name", "critical_low", "critical_high"],
			)
		}

		for obs in self.observations:
			param = params.get(obs.parameter_name)
			if not param or obs.numeric_value is None:
				obs.is_critical = 0
				continue

			is_crit = False
			if param.critical_low and obs.numeric_value < param.critical_low:
				is_crit = True
			if param.critical_high and obs.numeric_value > param.critical_high:
				is_crit = True
			obs.is_critical = 1 if is_crit else 0

	def _update_bedside_chart(self):
		if not self.bedside_chart:
			return

		if self.is_correction and self.corrects_entry:
			frappe.db.set_value(
				"IPD Chart Entry", self.corrects_entry, "status", "Corrected",
				update_modified=False,
			)

		frappe.db.set_value(
			"IPD Bedside Chart",
			self.bedside_chart,
			{
				"last_entry_at": self.entry_datetime or now_datetime(),
				"total_entries": (
					frappe.db.count(
						"IPD Chart Entry",
						{"bedside_chart": self.bedside_chart, "status": "Active"},
					)
				),
			},
			update_modified=False,
		)

		has_critical = any(o.is_critical for o in self.observations)
		if has_critical:
			self._raise_critical_alert()

	def _raise_critical_alert(self):
		critical_params = [o.parameter_name for o in self.observations if o.is_critical]
		ir_name = self.inpatient_record

		practitioner = frappe.db.get_value(
			"Inpatient Record", ir_name, "primary_practitioner"
		)
		if practitioner:
			practitioner_user = frappe.db.get_value(
				"Healthcare Practitioner", practitioner, "user_id"
			)
			if practitioner_user:
				notification = frappe.new_doc("Notification Log")
				notification.update({
					"for_user": practitioner_user,
					"from_user": frappe.session.user,
					"type": "Alert",
					"document_type": "IPD Chart Entry",
					"document_name": self.name,
					"subject": _(
						"CRITICAL: {0} for patient {1} — {2}"
					).format(
						self.chart_type,
						self.patient,
						", ".join(critical_params),
					),
				})
				notification.insert(ignore_permissions=True)

		frappe.publish_realtime(
			"critical_vital_alert",
			{
				"entry": self.name,
				"patient": self.patient,
				"inpatient_record": ir_name,
				"chart_type": self.chart_type,
				"critical_params": critical_params,
			},
			after_commit=True,
		)
