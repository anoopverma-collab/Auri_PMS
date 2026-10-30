"""Modules became shared: tag each existing module on the project it belonged to (Project > Enabled Modules)."""

import frappe


def execute() -> None:
	"""Add every project-bound Project Module to its project's Enabled Modules. Safe to run twice.

	Rows are inserted directly: patches run before the Project custom fields are synced."""
	for module in frappe.get_all(
		"Project Module", filters={"project": ["is", "set"]}, fields=["name", "project"]
	):
		if not frappe.db.exists("Project", module.project):
			continue
		filters = {"parent": module.project, "parentfield": "enabled_modules"}
		if frappe.db.exists("Project Enabled Module", {**filters, "module": module.name}):
			continue
		frappe.get_doc(
			{
				"doctype": "Project Enabled Module",
				**filters,
				"parenttype": "Project",
				"idx": frappe.db.count("Project Enabled Module", filters) + 1,
				"module": module.name,
			}
		).db_insert()
