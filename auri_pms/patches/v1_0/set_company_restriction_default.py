"""Store Projects Ignore Company Restrictions as ticked on sites that never saved it."""

import frappe


def execute() -> None:
	"""Write the ticked default once. A site that already saved the setting (ticked or not) is left as it is.

	Without a stored row the setting reads as ticked, but any code that loads PMS Settings and saves it
	would store the missing Check as 0 and switch the setting off by accident."""
	if frappe.db.exists(
		"Singles", {"doctype": "PMS Settings", "field": "projects_ignore_company_restrictions"}
	):
		return
	frappe.db.set_single_value("PMS Settings", "projects_ignore_company_restrictions", 1)
