"""Replace the Can Edit Planning Fields checkbox with Field Rules: a role without it gets the planning fields as view only."""

import frappe

PLANNING_FIELDS = (
	"subject",
	"project",
	"sprint",
	"release",
	"start_date",
	"due_date",
	"actual_start_date",
	"actual_end_date",
)


def execute() -> None:
	"""Safe to run twice. Rows are inserted directly: the old column is read with SQL."""
	if not frappe.db.has_column("Project Role", "can_edit_planning_fields"):
		return
	roles = frappe.db.sql(
		"select name from `tabProject Role` where ifnull(can_edit_planning_fields, 0) = 0", pluck=True
	)
	for role in roles:
		filters = {"parent": role, "parenttype": "Project Role", "parentfield": "field_rules"}
		if frappe.db.exists("Project Role Field Rule", filters):
			continue
		for idx, field in enumerate(PLANNING_FIELDS, start=1):
			frappe.get_doc(
				{"doctype": "Project Role Field Rule", **filters, "idx": idx, "field_name": field, "can_edit": 0}
			).db_insert()

	for role in frappe.get_all("Project Role", pluck="name"):
		doc = frappe.get_doc("Project Role", role)  # saving rewrites the Permissions summary
		doc.flags.ignore_permissions = True
		doc.save()
