"""Store the default status report section switches and ticket limits in PMS Settings."""

import frappe

DEFAULTS = {
	"show_report_modules": 1,
	"show_report_delivered": 1,
	"show_report_in_progress": 1,
	"show_report_waiting": 1,
	"show_report_next_up": 1,
	"show_report_issues": 1,
	"show_report_plan": 1,
	"show_report_risks": 1,
	"show_report_time": 1,
	"report_max_delivered": 40,
	"report_max_in_progress": 30,
	"report_max_waiting": 15,
	"report_max_next_up": 15,
	"report_max_overdue": 10,
}


def execute() -> None:
	"""Only fill values that were never saved, so a later choice is not overwritten."""
	stored = set(frappe.db.sql_list("select field from `tabSingles` where doctype = %s", "PMS Settings"))
	meta = frappe.get_meta("PMS Settings")
	for fieldname, value in DEFAULTS.items():
		if not meta.has_field(fieldname):
			continue  # a setting that no longer exists is not filled in
		if fieldname not in stored:
			frappe.db.set_single_value("PMS Settings", fieldname, value)
	frappe.clear_cache(doctype="PMS Settings")
