import frappe

RENAMES = (("Tracker User", "Auri PMS User"), ("Tracker Manager", "Auri PMS Manager"))


def execute():
	"""Rename the Tracker User / Tracker Manager roles; people, permissions and the app icon keep their access."""
	for old, new in RENAMES:
		if not frappe.db.exists("Role", old):
			continue
		if not frappe.db.exists("Role", new):
			frappe.rename_doc("Role", old, new, force=True)
			continue
		# both exist (the new one was created first): move everything over, then drop the old role
		for doctype in ("Has Role", "Custom DocPerm", "DocPerm"):
			table = frappe.qb.DocType(doctype)
			frappe.qb.update(table).set(table.role, new).where(table.role == old).run()
		frappe.delete_doc("Role", old, force=True, ignore_permissions=True)
