"""Remove the Tracker home workspace (its role is taken over by the Project Hub, Portfolio and My Work)."""

import frappe

HOME_CARDS = ("My Open Items", "My Overdue Items", "Opened This Week", "My Hours This Week")
HOME_CHARTS = ("Open Items by Status", "Open Items by Priority", "Hours by Project, last 30 days")


def execute() -> None:
	"""Delete the workspace, number cards and charts; rename the old app icon. Safe to run twice."""
	for doctype, names in (
		("Workspace", ("Tracker",)),
		("Number Card", HOME_CARDS),
		("Dashboard Chart", HOME_CHARTS),
	):
		for name in names:
			if frappe.db.exists(doctype, name):
				if doctype != "Workspace":
					frappe.db.set_value(
						doctype, name, "is_standard", 0
					)  # standard documents refuse deletion outside developer mode
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
	if frappe.db.exists("Desktop Icon", "Auri PMS") and not frappe.db.exists("Desktop Icon", "Tracker"):
		frappe.rename_doc("Desktop Icon", "Auri PMS", "Tracker", force=True)
		frappe.db.set_value("Desktop Icon", "Tracker", "label", "Tracker")
