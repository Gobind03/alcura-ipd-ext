"""Add dispense tracking fields to IPD Clinical Order
and delay/shift fields to IPD MAR Entry.

These fields are already defined in the DocType JSON files and will be
created by the model sync. This patch sets default values for existing records.
"""

from __future__ import annotations

import frappe


def execute():
	# Set default dispense_status on existing medication orders
	frappe.db.sql("""
		UPDATE `tabIPD Clinical Order`
		SET dispense_status = 'Pending', total_dispensed_qty = 0
		WHERE order_type = 'Medication'
		  AND (dispense_status IS NULL OR dispense_status = '')
	""")

	frappe.db.commit()
