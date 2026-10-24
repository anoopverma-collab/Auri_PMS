"""The Auri PMS sidebar and app icon on a site always match the files in the app."""

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from auri_pms import install
from auri_pms.auri_pms import boot


def read(folder: str) -> dict:
	with open(frappe.get_app_path("auri_pms", folder, "auri_pms.json")) as f:
		return json.load(f)


class TestWorkspace(IntegrationTestCase):
	def test_an_edited_or_older_copy_is_put_back_to_the_files(self):
		frappe.db.set_value("Workspace Sidebar", "Auri PMS", "title", "Edited by hand")
		frappe.db.sql(
			"delete from `tabWorkspace Sidebar Item` where parent = 'Auri PMS' and label = 'Sprint'"
		)
		install.ensure_workspace_docs()
		sidebar = frappe.get_doc("Workspace Sidebar", "Auri PMS")
		self.assertEqual(sidebar.title, read("workspace_sidebar")["title"])
		self.assertEqual(
			[(i.label, i.link_to) for i in sidebar.items],
			[(i["label"], i.get("link_to")) for i in read("workspace_sidebar")["items"]],
		)

	def test_a_stale_generated_sidebar_is_dropped_so_the_real_one_shows(self):
		"""Frappe keeps a generated "Auri PMS" sidebar in worker memory; with the real one present the cache is cleared."""
		from frappe.desk.doctype.workspace_sidebar import workspace_sidebar as ws

		generated = MagicMock(title="Auri PMS")
		fake = MagicMock(return_value=[generated])
		with patch.object(ws, "auto_generate_sidebar_from_module", fake):
			self.assertTrue(boot.drop_stale_generated_sidebar())
			fake.clear_cache.assert_called_once()
		clean = MagicMock(return_value=[MagicMock(title="Other module")])
		with patch.object(ws, "auto_generate_sidebar_from_module", clean):
			self.assertFalse(boot.drop_stale_generated_sidebar())
			clean.clear_cache.assert_not_called()

	def test_the_app_icon_has_each_role_once(self):
		install.ensure_workspace_docs()
		install.ensure_workspace_docs()
		roles = [r.role for r in frappe.get_doc("Desktop Icon", "Auri PMS").roles]
		self.assertCountEqual(roles, [r["role"] for r in read("desktop_icon")["roles"]])


class TestRoleRename(IntegrationTestCase):
	def test_people_with_an_old_role_name_move_to_the_new_one(self):
		from auri_pms.patches.v1_0 import rename_tracker_roles

		user = "role.rename.test@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Rename", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Role", "role_name": "Tracker User"}).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Tracker User")
		rename_tracker_roles.execute()
		frappe.clear_cache(user=user)  # roles are cached per user
		roles = frappe.get_roles(user)
		self.assertIn("Auri PMS User", roles)
		self.assertNotIn("Tracker User", roles)
		self.assertFalse(frappe.db.exists("Role", "Tracker User"))
