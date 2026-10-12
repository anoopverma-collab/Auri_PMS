"""Store the default risk and health thresholds in PMS Settings (a Single keeps no value for a field added later)."""

import frappe

DEFAULTS = {
	"risk_medium_from": 5,
	"risk_high_from": 10,
	"risk_critical_from": 15,
	"overdue_amber_pct": 10,
	"overdue_red_pct": 25,
	"burndown_amber_pct": 10,
	"burndown_red_pct": 25,
	"effort_ahead_amber_pct": 25,
	"release_progress_pct": 80,
	"release_due_soon_days": 7,
	"backlog_growth_ratio": 1.5,
	"backlog_growth_min_created": 4,
	"score_red_penalty": 25,
	"score_amber_penalty": 10,
}


def execute() -> None:
	for fieldname, value in DEFAULTS.items():
		if frappe.db.get_single_value("PMS Settings", fieldname) in (None, "", 0, "0"):
			frappe.db.set_single_value("PMS Settings", fieldname, value)
	frappe.clear_cache(doctype="PMS Settings")
