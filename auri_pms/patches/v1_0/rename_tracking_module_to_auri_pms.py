"""Rename the Tracking module to Auri PMS (the Python package moved from ``tracking`` to ``auri_pms``)."""

import frappe

OLD, NEW = "Tracking", "Auri PMS"
MODULE_TABLES = (
	"DocType",
	"Page",
	"Report",
	"Custom Field",
	"Property Setter",
	"Notification",
	"Number Card",
	"Dashboard Chart",
	"Workspace",
)


def execute() -> None:
	"""Move every record of the old module to the new one and drop job entries that point at the old package."""
	if not frappe.db.exists("Module Def", OLD):
		return
	# Frappe refuses to rename an app's own (non-custom) module, so create the new one and move the records over.
	if not frappe.db.exists("Module Def", NEW):
		frappe.get_doc({"doctype": "Module Def", "module_name": NEW, "app_name": "auri_pms"}).insert(
			ignore_permissions=True
		)
	for doctype in MODULE_TABLES:
		if frappe.db.has_column(doctype, "module"):
			table = frappe.qb.DocType(doctype)
			frappe.qb.update(table).set(table.module, NEW).where(table.module == OLD).run()
	frappe.db.delete("Module Def", OLD)
	for job in frappe.get_all(
		"Scheduled Job Type", filters={"method": ["like", "auri_pms.tracking.%"]}, pluck="name"
	):
		frappe.delete_doc("Scheduled Job Type", job, force=True, ignore_permissions=True)
	for doctype in ("Workspace Sidebar", "Desktop Icon"):
		if frappe.db.exists(doctype, OLD):
			frappe.delete_doc(doctype, OLD, force=True, ignore_permissions=True)
