"""Rename the Tracker Settings DocType to PMS Settings on sites installed before the rename."""

import frappe


def execute() -> None:
	"""Rename the single DocType together with its stored values. Safe to run twice."""
	if frappe.db.exists("DocType", "Tracker Settings") and not frappe.db.exists("DocType", "PMS Settings"):
		frappe.rename_doc("DocType", "Tracker Settings", "PMS Settings", force=True)
