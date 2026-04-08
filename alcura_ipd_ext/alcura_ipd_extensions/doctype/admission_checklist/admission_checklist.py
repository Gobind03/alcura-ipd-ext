"""Controller for Admission Checklist."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class AdmissionChecklist(Document):
	def validate(self):
		self._validate_inpatient_record()

	def _validate_inpatient_record(self):
		if not self.inpatient_record:
			return

		ir_patient = frappe.db.get_value(
			"Inpatient Record", self.inpatient_record, "patient"
		)
		if ir_patient and self.patient and ir_patient != self.patient:
			frappe.throw(
				_("Patient {0} does not match Inpatient Record {1} patient {2}.").format(
					frappe.bold(self.patient),
					frappe.bold(self.inpatient_record),
					frappe.bold(ir_patient),
				)
			)
