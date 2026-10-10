"""The app's sidebar and icon are called Auri PMS now (they were called Tracker)."""

import frappe


def execute() -> None:
	"""Drop the old Tracker sidebar and icon once the Auri PMS ones were imported (or rename them). Safe to run twice."""
	for doctype in ("Workspace Sidebar", "Desktop Icon"):
		if not frappe.db.exists(doctype, "Tracker"):
			continue
		if frappe.db.exists(doctype, "Auri PMS"):
			# database rows only: delete_doc would also remove standard JSON files in developer mode
			if doctype == "Workspace Sidebar":
				frappe.db.delete("Workspace Sidebar Item", {"parent": "Tracker"})
			frappe.db.delete(doctype, {"name": "Tracker"})
		else:
			frappe.rename_doc(doctype, "Tracker", "Auri PMS", force=True)
	if frappe.db.exists("Desktop Icon", "Auri PMS"):
		frappe.db.set_value("Desktop Icon", "Auri PMS", {"label": "Auri PMS", "link_to": "Auri PMS"})
