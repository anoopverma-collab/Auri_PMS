"""Replace the site-wide Members See All Work Items switch with Can See All Work Items on each Project Role.

Keeps what members see today: with the switch ticked (or never saved) every role sees all; unticked, only the roles
that can manage members do."""

import frappe


def execute() -> None:
	"""Safe to run twice: a role that already has the box ticked stays ticked."""
	row = frappe.db.sql(
		"select value from `tabSingles` where doctype = 'PMS Settings' and field = 'members_see_all_work_items'"
	)
	everyone = True if not row else bool(int(row[0][0] or 0))
	for role in frappe.get_all("Project Role", fields=["name", "can_manage_members"]):
		see_all = 1 if everyone else int(role.can_manage_members or 0)
		if see_all:
			frappe.db.set_value("Project Role", role.name, "can_see_all_items", 1)
