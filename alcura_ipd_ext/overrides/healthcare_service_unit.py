"""Server-side hook for Healthcare Service Unit occupancy sync.

Registered via ``doc_events`` in hooks.py. When the standard admission/discharge
flow changes an HSU leaf node's ``occupancy_status``, this hook propagates the
change to the linked Hospital Bed and triggers capacity rollup.
"""

import frappe


def on_update(doc, method=None):
	"""Sync occupancy_status from HSU to the linked Hospital Bed."""
	if not doc.get("inpatient_occupancy"):
		return

	previous = doc.get_doc_before_save()
	if not previous:
		return

	old_status = previous.get("occupancy_status")
	new_status = doc.get("occupancy_status")

	if old_status == new_status:
		return

	from alcura_ipd_ext.utils.bed_helpers import sync_bed_occupancy_from_hsu

	sync_bed_occupancy_from_hsu(doc.name, new_status)
