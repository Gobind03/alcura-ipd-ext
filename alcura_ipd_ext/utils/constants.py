"""Shared constants for alcura_ipd_ext.

Central source of truth for option lists used across multiple doctypes,
services, and custom field definitions. Import from here instead of
duplicating option strings.
"""

PAYER_TYPE_OPTIONS = "\nCash\nCorporate\nInsurance TPA\nPSU\nGovernment Scheme"

PAYER_TYPES_REQUIRING_CUSTOMER = ("Corporate", "PSU")
PAYER_TYPES_REQUIRING_INSURANCE_PAYOR = ("Insurance TPA",)
PAYER_TYPES_NON_CASH = ("Corporate", "Insurance TPA", "PSU", "Government Scheme")

RELATIONSHIP_OPTIONS = "\nSelf\nSpouse\nChild\nParent\nSibling\nDependent\nOther"

# ── Clinical Order constants ─────────────────────────────────────────

ORDER_TYPE_OPTIONS = "\nMedication\nLab Test\nRadiology\nProcedure"

ORDER_URGENCY_OPTIONS = "Routine\nUrgent\nSTAT\nEmergency"

ORDER_STATUS_OPTIONS = (
	"Draft\nOrdered\nAcknowledged\nIn Progress\nCompleted\nCancelled\nOn Hold"
)

ORDER_ACTIVE_STATUSES = ("Draft", "Ordered", "Acknowledged", "In Progress", "On Hold")
ORDER_TERMINAL_STATUSES = ("Completed", "Cancelled")
ORDER_ACTIONABLE_STATUSES = ("Ordered", "Acknowledged", "In Progress")

ROUTE_OPTIONS = "\nOral\nIV\nIM\nSC\nSL\nTopical\nInhaled\nRectal\nPR\nOther"

FREQUENCY_OPTIONS = (
	"\nOnce\nOD\nBD\nTDS\nQID\nQ4H\nQ6H\nQ8H\nQ12H\nPRN\nSTAT\nContinuous"
)
