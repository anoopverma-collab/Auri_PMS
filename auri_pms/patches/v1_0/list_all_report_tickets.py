"""List every ticket in the status report: move the old default section limits to 0 (no limit)."""

import frappe

OLD_DEFAULTS = {
	"report_max_delivered": 40,
	"report_max_in_progress": 30,
	"report_max_waiting": 15,
	"report_max_next_up": 15,
	"report_max_overdue": 10,
}


def execute() -> None:
	"""Only values still at the old default change; a limit somebody chose themselves is kept."""
	meta = frappe.get_meta("PMS Settings")
	for fieldname, old in OLD_DEFAULTS.items():
		if not meta.has_field(fieldname):
			continue  # the per-section limits were removed from PMS Settings; nothing left to change
		current = frappe.db.get_single_value("PMS Settings", fieldname)
		if current in (None, "") or int(current) == old:
			frappe.db.set_single_value("PMS Settings", fieldname, 0)
	frappe.clear_cache(doctype="PMS Settings")
