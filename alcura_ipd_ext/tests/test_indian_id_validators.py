"""Unit tests for Indian statutory ID validators.

These are pure-function tests with no Frappe DB dependency.
"""

import pytest

from alcura_ipd_ext.utils.indian_id_validators import (
	validate_aadhaar,
	validate_abha_address,
	validate_abha_number,
	validate_indian_mobile,
	validate_pan,
)


# ---------------------------------------------------------------------------
# Aadhaar
# ---------------------------------------------------------------------------

class TestValidateAadhaar:
	def test_none_is_valid(self):
		ok, err = validate_aadhaar(None)
		assert ok is True
		assert err is None

	def test_empty_string_is_valid(self):
		ok, err = validate_aadhaar("")
		assert ok is True

	def test_valid_aadhaar(self):
		# 499118665246 passes Verhoeff
		ok, err = validate_aadhaar("499118665246")
		assert ok is True, err

	def test_valid_aadhaar_with_spaces(self):
		ok, err = validate_aadhaar("4991 1866 5246")
		assert ok is True, err

	def test_valid_aadhaar_with_dashes(self):
		ok, err = validate_aadhaar("4991-1866-5246")
		assert ok is True, err

	def test_too_short(self):
		ok, err = validate_aadhaar("12345")
		assert ok is False
		assert "12 digits" in err

	def test_too_long(self):
		ok, err = validate_aadhaar("1234567890123")
		assert ok is False

	def test_non_numeric(self):
		ok, err = validate_aadhaar("49911866524A")
		assert ok is False

	def test_starts_with_zero(self):
		ok, err = validate_aadhaar("099118665246")
		assert ok is False
		assert "cannot start with 0" in err

	def test_starts_with_one(self):
		ok, err = validate_aadhaar("199118665246")
		assert ok is False
		assert "cannot start with" in err

	def test_bad_checksum(self):
		ok, err = validate_aadhaar("499118665247")
		assert ok is False
		assert "checksum" in err.lower()


# ---------------------------------------------------------------------------
# PAN
# ---------------------------------------------------------------------------

class TestValidatePan:
	def test_none_is_valid(self):
		ok, _ = validate_pan(None)
		assert ok is True

	def test_empty_is_valid(self):
		ok, _ = validate_pan("")
		assert ok is True

	def test_valid_pan(self):
		ok, err = validate_pan("ABCDE1234F")
		assert ok is True, err

	def test_valid_pan_lowercase(self):
		ok, err = validate_pan("abcde1234f")
		assert ok is True, err

	def test_too_short(self):
		ok, err = validate_pan("ABCDE1234")
		assert ok is False

	def test_wrong_format_digits_first(self):
		ok, err = validate_pan("12345ABCDE")
		assert ok is False

	def test_wrong_format_all_letters(self):
		ok, err = validate_pan("ABCDEFGHIJ")
		assert ok is False

	def test_with_spaces(self):
		ok, err = validate_pan("ABCDE 1234F")
		assert ok is False


# ---------------------------------------------------------------------------
# ABHA Number
# ---------------------------------------------------------------------------

class TestValidateAbhaNumber:
	def test_none_is_valid(self):
		ok, _ = validate_abha_number(None)
		assert ok is True

	def test_valid_14_digit(self):
		ok, err = validate_abha_number("12345678901234")
		assert ok is True, err

	def test_valid_with_spaces(self):
		ok, err = validate_abha_number("1234 5678 9012 34")
		assert ok is True, err

	def test_too_short(self):
		ok, err = validate_abha_number("1234567890")
		assert ok is False
		assert "14 digits" in err

	def test_non_numeric(self):
		ok, err = validate_abha_number("1234567890123A")
		assert ok is False


# ---------------------------------------------------------------------------
# ABHA Address
# ---------------------------------------------------------------------------

class TestValidateAbhaAddress:
	def test_none_is_valid(self):
		ok, _ = validate_abha_address(None)
		assert ok is True

	def test_valid_address(self):
		ok, err = validate_abha_address("username@abdm")
		assert ok is True, err

	def test_valid_with_dots_underscores(self):
		ok, err = validate_abha_address("user.name_123@abdm")
		assert ok is True, err

	def test_wrong_domain(self):
		ok, err = validate_abha_address("user@gmail.com")
		assert ok is False
		assert "@abdm" in err

	def test_no_at_sign(self):
		ok, err = validate_abha_address("username")
		assert ok is False

	def test_uppercase_normalised(self):
		ok, err = validate_abha_address("UserName@ABDM")
		assert ok is True, err


# ---------------------------------------------------------------------------
# Indian Mobile
# ---------------------------------------------------------------------------

class TestValidateIndianMobile:
	def test_none_is_valid(self):
		ok, _ = validate_indian_mobile(None)
		assert ok is True

	def test_valid_10_digit(self):
		ok, err = validate_indian_mobile("9876543210")
		assert ok is True, err

	def test_valid_with_plus91(self):
		ok, err = validate_indian_mobile("+919876543210")
		assert ok is True, err

	def test_valid_with_91_prefix(self):
		ok, err = validate_indian_mobile("919876543210")
		assert ok is True, err

	def test_valid_with_zero_prefix(self):
		ok, err = validate_indian_mobile("09876543210")
		assert ok is True, err

	def test_valid_with_spaces(self):
		ok, err = validate_indian_mobile("98765 43210")
		assert ok is True, err

	def test_starts_with_5_invalid(self):
		ok, err = validate_indian_mobile("5876543210")
		assert ok is False
		assert "starting with 6-9" in err

	def test_too_short(self):
		ok, err = validate_indian_mobile("98765")
		assert ok is False

	def test_non_numeric(self):
		ok, err = validate_indian_mobile("98765ABCDE")
		assert ok is False
