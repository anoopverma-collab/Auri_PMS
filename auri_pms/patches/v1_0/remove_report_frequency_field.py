"""Weekly and monthly reports are now independent: drop the short-lived exclusive "Send" (frequency) field."""

import frappe


def execute() -> None:
	name = "Project-tracker_report_frequency"
	if not frappe.db.exists("Custom Field", name):
		return
	# a project that was set to Monthly only keeps just its monthly schedule
	if frappe.db.has_column("Project", "tracker_report_frequency"):
		frappe.db.sql(
			"update `tabProject` set tracker_report_weekday = '' where tracker_report_frequency = 'Monthly'"
		)
	frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
