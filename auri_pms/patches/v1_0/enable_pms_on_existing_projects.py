"""Tick Enable Auri PMS on every project that already has an identifier (they were Auri PMS projects before)."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute() -> None:
	"""Create the checkbox first (fixtures are imported after patches), then enable existing projects."""
	create_custom_fields(
		{
			"Project": [
				{
					"fieldname": "pms_enabled",
					"fieldtype": "Check",
					"label": "Enable Auri PMS",
					"default": "0",
					"in_standard_filter": 1,
					"insert_after": "tab_tracker",
					"module": "Auri PMS",
				}
			]
		}
	)
	project = frappe.qb.DocType("Project")
	(
		frappe.qb.update(project)
		.set(project.pms_enabled, 1)
		.where(project.tracker_identifier.isnotnull() & (project.tracker_identifier != ""))
		.run()
	)
