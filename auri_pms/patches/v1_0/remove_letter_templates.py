"""Remove the Client Letter and PMS Letter email templates (and stop using them as the default)."""

import frappe

REMOVED = ("PMS Status Report - Client Letter", "PMS Letter - Blue", "PMS Letter - Auriga Blue")


def execute() -> None:
	if frappe.db.get_single_value("PMS Settings", "report_email_template") in REMOVED:
		frappe.db.set_single_value("PMS Settings", "report_email_template", "")
	for name in REMOVED:
		if frappe.db.exists("Email Template", name):
			frappe.delete_doc("Email Template", name, force=True, ignore_permissions=True)
	frappe.clear_cache(doctype="PMS Settings")
