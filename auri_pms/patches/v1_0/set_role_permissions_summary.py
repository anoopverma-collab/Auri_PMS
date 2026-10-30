"""Fill the Permissions column of the Project Role list for roles saved before it existed."""

import frappe


def execute() -> None:
	"""Save each Project Role once so validate writes its Permissions text. Safe to run twice."""
	for name in frappe.get_all("Project Role", pluck="name"):
		role = frappe.get_doc("Project Role", name)
		role.flags.ignore_permissions = True
		role.save()
