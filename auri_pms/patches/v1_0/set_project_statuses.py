"""Give every Auri PMS project an explicit Enabled Statuses list (all active statuses) so nothing depends on an empty table."""

import frappe


def execute() -> None:
	"""Fill the Enabled Statuses table of projects that have none. Safe to run twice.

	Rows are inserted directly: patches run before the Project custom fields are synced."""
	statuses = frappe.get_all("Work Item Status", filters={"is_active": 1}, pluck="name", order_by="sequence")
	for project in frappe.get_all("Project", filters={"pms_enabled": 1}, pluck="name"):
		if frappe.db.exists(
			"Project Work Item Status", {"parent": project, "parentfield": "enabled_statuses"}
		):
			continue
		for idx, status in enumerate(statuses, start=1):
			frappe.get_doc(
				{
					"doctype": "Project Work Item Status",
					"parent": project,
					"parenttype": "Project",
					"parentfield": "enabled_statuses",
					"idx": idx,
					"status": status,
				}
			).db_insert()
