"""Project Role > Can See Health & Cost and Can See Auri Insights: tick them for the Manager role only.

The roles that can manage members (the shipped Manager) get both; every other role starts unticked."""

import frappe


def execute() -> None:
	"""Safe to run twice: a role that already has a box ticked keeps it."""
	for name in frappe.get_all("Project Role", filters={"can_manage_members": 1}, pluck="name"):
		role = frappe.get_doc("Project Role", name)
		role.can_see_health_cost = 1
		role.can_see_insights = 1
		role.flags.ignore_permissions = True
		role.save()  # saving also rewrites the Permissions summary of the list
