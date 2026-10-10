"""Rename the Tracker DocType (and its two child tables) to Ticket Type on sites installed before the rename."""

import frappe

RENAMES = (
	("Tracker Transition", "Ticket Type Transition"),
	("Project Tracker", "Project Ticket Type"),
	("Tracker", "Ticket Type"),  # last: the parent of the two tables above
)


def execute() -> None:
	"""Rename each DocType that still has the old name (data, links and custom-field options follow). Safe to run twice."""
	for old, new in RENAMES:
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
			frappe.rename_doc("DocType", old, new, force=True)
