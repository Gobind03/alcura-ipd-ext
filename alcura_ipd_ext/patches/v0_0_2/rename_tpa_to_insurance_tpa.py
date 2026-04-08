"""Rename payer_type value "TPA" to "Insurance TPA" across all custom doctypes.

This patch aligns the payer_type Select field with the expanded 5-value set
introduced alongside the Patient Payer Profile doctype.

Affected doctypes:
- Room Tariff Mapping
- Bed Reservation
"""

from __future__ import annotations

import frappe


def execute():
	_rename_in_doctype("Room Tariff Mapping", "payer_type")
	_rename_in_doctype("Bed Reservation", "payer_type")


def _rename_in_doctype(doctype: str, fieldname: str):
	table = frappe.qb.DocType(doctype)
	count = (
		frappe.qb.from_(table)
		.where(table[fieldname] == "TPA")
		.select(frappe.qb.functions.Count("*"))
		.run()[0][0]
	)

	if not count:
		return

	frappe.db.sql(
		f"UPDATE `tab{doctype}` SET `{fieldname}` = 'Insurance TPA' WHERE `{fieldname}` = 'TPA'"
	)
	frappe.db.commit()
	frappe.logger("alcura_ipd_ext").info(
		f"Renamed {count} '{doctype}' record(s): payer_type TPA -> Insurance TPA"
	)
