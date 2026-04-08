"""Pure-function validators for Indian statutory identifiers.

All validators return ``(is_valid: bool, error_message: str | None)`` so
callers can decide whether to raise, warn, or log.
"""

import re

# ---------------------------------------------------------------------------
# Verhoeff algorithm tables for Aadhaar checksum
# ---------------------------------------------------------------------------

_VERHOEFF_D = [
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
	[1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
	[2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
	[3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
	[4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
	[5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
	[6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
	[7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
	[8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
	[9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
	[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
	[1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
	[5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
	[8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
	[9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
	[4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
	[2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
	[7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def _verhoeff_checksum(number_str: str) -> int:
	"""Compute the Verhoeff checksum for a numeric string.
	Returns 0 if the number (including its check digit) is valid."""
	c = 0
	for i, ch in enumerate(reversed(number_str)):
		c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
	return c


# ---------------------------------------------------------------------------
# Public validators
# ---------------------------------------------------------------------------

_AADHAAR_RE = re.compile(r"^\d{12}$")
_PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
_ABHA_NUMBER_RE = re.compile(r"^\d{14}$")
_ABHA_ADDRESS_RE = re.compile(r"^[a-zA-Z0-9._]+@abdm$")
_INDIAN_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def validate_aadhaar(value: str | None) -> tuple[bool, str | None]:
	"""Validate a 12-digit Aadhaar number with Verhoeff checksum."""
	if not value:
		return True, None

	cleaned = value.strip().replace(" ", "").replace("-", "")

	if not _AADHAAR_RE.match(cleaned):
		return False, "Aadhaar number must be exactly 12 digits"

	if cleaned[0] == "0" or cleaned[0] == "1":
		return False, "Aadhaar number cannot start with 0 or 1"

	if _verhoeff_checksum(cleaned) != 0:
		return False, "Aadhaar number has an invalid checksum"

	return True, None


def validate_pan(value: str | None) -> tuple[bool, str | None]:
	"""Validate Indian PAN in AAAAA9999A format."""
	if not value:
		return True, None

	cleaned = value.strip().upper()

	if not _PAN_RE.match(cleaned):
		return False, "PAN must be in AAAAA9999A format (5 letters, 4 digits, 1 letter)"

	return True, None


def validate_abha_number(value: str | None) -> tuple[bool, str | None]:
	"""Validate 14-digit ABHA (Ayushman Bharat Health Account) number."""
	if not value:
		return True, None

	cleaned = value.strip().replace(" ", "").replace("-", "")

	if not _ABHA_NUMBER_RE.match(cleaned):
		return False, "ABHA number must be exactly 14 digits"

	return True, None


def validate_abha_address(value: str | None) -> tuple[bool, str | None]:
	"""Validate ABHA address format (e.g. username@abdm)."""
	if not value:
		return True, None

	cleaned = value.strip().lower()

	if not _ABHA_ADDRESS_RE.match(cleaned):
		return False, "ABHA address must be in the format username@abdm"

	return True, None


def validate_indian_mobile(value: str | None) -> tuple[bool, str | None]:
	"""Validate a 10-digit Indian mobile number starting with 6-9."""
	if not value:
		return True, None

	cleaned = value.strip().replace(" ", "").replace("-", "")
	if cleaned.startswith("+91"):
		cleaned = cleaned[3:]
	elif cleaned.startswith("91") and len(cleaned) == 12:
		cleaned = cleaned[2:]
	elif cleaned.startswith("0"):
		cleaned = cleaned[1:]

	if not _INDIAN_MOBILE_RE.match(cleaned):
		return False, "Mobile number must be a valid 10-digit Indian number starting with 6-9"

	return True, None
