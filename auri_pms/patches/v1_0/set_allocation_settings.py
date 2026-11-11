"""Store the default allocation & utilisation settings in PMS Settings (a Single keeps no value for a field added later)."""

import frappe

DEFAULTS = {"utilisation_window_weeks": 4, "over_utilisation_pct": 110, "under_utilisation_pct": 50}


def execute() -> None:
	stored = set(frappe.db.sql_list("select field from `tabSingles` where doctype = %s", "PMS Settings"))
	for fieldname, value in DEFAULTS.items():
		if fieldname not in stored:
			frappe.db.set_single_value("PMS Settings", fieldname, value)
	frappe.clear_cache(doctype="PMS Settings")
