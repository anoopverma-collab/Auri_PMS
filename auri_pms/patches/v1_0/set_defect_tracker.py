"""Mark the shipped Bug ticket type as a defect type on sites that were installed before the Quality dashboard."""

import frappe


def execute() -> None:
	"""Set is_defect on the Bug tracker (once); ticket types a client renamed or edited are not touched."""
	if frappe.db.exists("Ticket Type", "Bug") and not frappe.db.get_value("Ticket Type", "Bug", "is_defect"):
		frappe.db.set_value("Ticket Type", "Bug", "is_defect", 1)
