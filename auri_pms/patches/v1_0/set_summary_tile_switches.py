"""Store the default (on) for the summary tile switches (a Single keeps no value for a field added later)."""

import frappe

TILES = ("delivered", "open", "overdue", "waiting", "time")


def execute() -> None:
	stored = set(frappe.db.sql_list("select field from `tabSingles` where doctype = %s", "PMS Settings"))
	for tile in TILES:
		if f"show_report_tile_{tile}" not in stored:
			frappe.db.set_single_value("PMS Settings", f"show_report_tile_{tile}", 1)
	frappe.clear_cache(doctype="PMS Settings")
