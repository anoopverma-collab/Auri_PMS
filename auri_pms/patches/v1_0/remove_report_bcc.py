"""BCC was removed from the client status report: drop the Report BCC custom field from Project."""

import frappe


def execute() -> None:
	name = "Project-tracker_report_bcc"
	if frappe.db.exists("Custom Field", name):
		frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
