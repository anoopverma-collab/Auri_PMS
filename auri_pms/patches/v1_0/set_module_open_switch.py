"""Store the default (on) for "Show Open Count in Progress by Module" (a Single keeps no value for a field added later)."""

import frappe


def execute() -> None:
	stored = set(frappe.db.sql_list("select field from `tabSingles` where doctype = %s", "PMS Settings"))
	if "show_report_modules_open" not in stored:
		frappe.db.set_single_value("PMS Settings", "show_report_modules_open", 1)
	frappe.clear_cache(doctype="PMS Settings")
