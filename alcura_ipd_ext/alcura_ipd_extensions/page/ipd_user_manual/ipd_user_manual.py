import frappe
from pathlib import Path


@frappe.whitelist()
def get_manual_html():
	"""Return the IPD User Manual as rendered HTML."""
	md_path = Path(frappe.get_app_path("alcura_ipd_ext")).parent / "docs" / "USER_MANUAL.md"

	if not md_path.exists():
		frappe.throw("User manual file not found.", frappe.DoesNotExistError)

	md_content = md_path.read_text(encoding="utf-8")
	return frappe.utils.md_to_html(md_content)
