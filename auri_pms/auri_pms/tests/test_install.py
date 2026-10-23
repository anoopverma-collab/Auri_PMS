"""Install, default data and fixtures (T-001 .. T-003)."""

import frappe
from frappe.tests import IntegrationTestCase

from auri_pms import install


class TestInstall(IntegrationTestCase):
	def counts(self) -> dict:
		doctypes = (
			"Work Item Status",
			"Project Role",
			"Ticket Type",
			"Ticket Type Transition",
			"Activity Type",
		)
		result = {d: frappe.db.count(d) for d in doctypes}
		result["columns"] = len(frappe.get_doc("Kanban Board", install.BOARD_NAME).columns)
		return result

	def test_t001_after_install_twice_no_duplicates(self):
		"""T-001: running after_install twice creates no duplicates and raises no error."""
		install.after_install()
		before = self.counts()
		install.after_install()
		self.assertEqual(before, self.counts())
		self.assertEqual(frappe.db.count("Work Item Status", {"name": "New"}), 1)

	def test_t002_migrate_keeps_edited_colour(self):
		"""T-002: an edited status colour survives migrate hooks and default-data re-runs."""
		frappe.db.set_value("Work Item Status", "New", "color", "#112233")
		for hook in frappe.get_hooks("after_migrate"):
			frappe.get_attr(hook)()
		install.create_default_data()
		self.assertEqual(frappe.db.get_value("Work Item Status", "New", "color"), "#112233")

	def test_t003_fixtures_exist(self):
		"""T-003: roles, custom fields, workspace and Kanban board exist."""
		for role in ("Auri PMS Manager", "Auri PMS User"):
			self.assertTrue(frappe.db.exists("Role", role), role)
		for fieldname in (
			"tab_tracker",
			"tracker_identifier",
			"parent_project",
			"is_public",
			"tracker_members",
			"enabled_trackers",
		):
			self.assertTrue(frappe.db.exists("Custom Field", f"Project-{fieldname}"), fieldname)
		for fieldname in ("tracker_project", "tracker_default_tracker"):
			self.assertTrue(frappe.db.exists("Custom Field", f"Email Account-{fieldname}"), fieldname)
		# the app has no home workspace: the sidebar starts with the Project Hub and the icon is called Tracker
		self.assertFalse(frappe.db.exists("Workspace", "Tracker"))
		sidebar = frappe.get_doc("Workspace Sidebar", "Auri PMS")
		self.assertEqual(sidebar.items[0].link_to, "project-hub")
		self.assertNotIn("Home", [i.label for i in sidebar.items])
		self.assertTrue(frappe.db.exists("Desktop Icon", "Auri PMS"))
		board = frappe.get_doc("Kanban Board", install.BOARD_NAME)
		self.assertEqual([c.column_name for c in board.columns], [s[0] for s in install.STATUSES])

	def test_tracker_roles_can_use_erpnext_doctypes(self):
		"""Tracker roles may read Project and Activity Type (needed to log time) and Auri PMS Users may edit Project."""
		for doctype, role, ptype in (
			("Project", "Auri PMS User", "read"),
			("Project", "Auri PMS User", "write"),
			("Project", "Auri PMS Manager", "create"),
			("Project", "System Manager", "read"),
			("Project", "System Manager", "create"),
			("Activity Type", "Auri PMS User", "read"),
			("Activity Type", "Auri PMS Manager", "read"),
		):
			self.assertTrue(
				frappe.db.get_value(
					"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}, ptype
				),
				f"{role} {ptype} on {doctype}",
			)
