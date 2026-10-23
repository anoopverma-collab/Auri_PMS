"""Fill the Role Permissions column of existing project members."""

import frappe

from auri_pms.auri_pms.project_hooks import get_role_permissions


def execute() -> None:
	frappe.reload_doc("auri_pms", "doctype", "project_member")
	for row in frappe.get_all("Project Member", fields=["name", "project_role"]):
		if row.project_role:
			frappe.db.set_value(
				"Project Member",
				row.name,
				"role_permissions",
				get_role_permissions(row.project_role),
				update_modified=False,
			)
