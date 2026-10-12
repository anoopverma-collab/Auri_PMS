"""Store the default for the two status report summary switches (a Single keeps no value for a field added later)."""

import frappe

DEFAULTS = {"show_report_created": 1, "show_report_completion": 1}


def execute() -> None:
	stored = set(frappe.db.sql_list("select field from `tabSingles` where doctype = %s", "PMS Settings"))
	for fieldname, value in DEFAULTS.items():
		if fieldname not in stored:
			frappe.db.set_single_value("PMS Settings", fieldname, value)
	frappe.clear_cache(doctype="PMS Settings")
