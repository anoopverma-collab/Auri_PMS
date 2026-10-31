"""Auri PMS Admin sees everything; Auri PMS Manager works like a member and sees only the projects they are on."""

import frappe

from auri_pms.auri_pms import api
from auri_pms.auri_pms.tests.utils import BOSS, DEV, TM, TrackerTestCase
from auri_pms.auri_pms.utils import get_capabilities, is_admin, portfolio_projects


class TestRoles(TrackerTestCase):
	def join(self, project, user, role):
		doc = frappe.get_doc("Project", project)
		doc.append("tracker_members", {"user": user, "project_role": role})
		doc.save(ignore_permissions=True)

	def projects(self, user):
		with self.as_user(user):
			return {
				p.name for p in frappe.get_list("Project", filters={"pms_enabled": 1}, limit_page_length=0)
			}

	def test_only_admins_are_unrestricted(self):
		self.assertTrue(is_admin(TM))
		self.assertFalse(is_admin(BOSS))

	def test_a_manager_with_no_project_sees_only_public_projects(self):
		"""Auri PMS Manager and no membership: private projects stay hidden, and there is no Portfolio."""
		self.new_item(DEV, subject="hidden")
		self.assertNotIn(self.ALP, self.projects(BOSS))  # private
		self.assertIn(self.BET, self.projects(BOSS))  # public: visible, read-only
		with self.as_user(BOSS):
			self.assertNotIn(self.ALP, {p["name"] for p in api.get_hub_projects()})
			self.assertFalse(frappe.get_list("Work Item", filters={"project": self.ALP}))
			self.assertEqual(portfolio_projects(BOSS), [])
			self.assertThrows("Health and cost", lambda: api.get_portfolio("3m"), frappe.PermissionError)

	def test_a_manager_sees_the_projects_they_are_allocated_to(self):
		self.join(self.ALP, BOSS, "Developer")
		self.new_item(DEV, subject="visible")
		self.assertIn(self.ALP, self.projects(BOSS))
		with self.as_user(BOSS):
			self.assertTrue(frappe.get_list("Work Item", filters={"project": self.ALP}))
			self.assertFalse(
				get_capabilities(self.ALP)["can_manage_members"]
			)  # their Project Role decides, not the role

	def test_a_project_manager_role_opens_the_portfolio_for_that_project(self):
		self.join(self.ALP, BOSS, "Manager")
		self.assertEqual(portfolio_projects(BOSS), [self.ALP])
		with self.as_user(BOSS):
			self.assertEqual({p.name for p in api.get_portfolio("3m").projects}, {self.ALP})

	def test_an_admin_sees_every_project_without_being_a_member(self):
		self.assertTrue({self.ALP, self.BET} <= self.projects(TM))
		with self.as_user(TM):
			self.assertTrue(all(get_capabilities(self.ALP).values()))
			self.assertTrue({self.ALP, self.BET} <= set(portfolio_projects(TM)))

	def test_the_roles_come_from_the_code(self):
		"""ensure_roles creates the roles when missing, and Admin holds every DocType right a Manager holds."""
		from auri_pms import install

		frappe.delete_doc("Role", "Auri PMS Admin", force=True, ignore_permissions=True)
		install.ensure_roles()
		self.assertTrue(frappe.db.exists("Role", "Auri PMS Admin"))
		rights = ("read", "write", "create", "delete", "import", "report")
		for doctype in frappe.get_all("DocType", filters={"module": "Auri PMS", "istable": 0}, pluck="name"):
			perms = {
				p.role: p
				for p in frappe.get_all(
					"DocPerm",
					filters={"parent": doctype, "role": ["in", ["Auri PMS Manager", "Auri PMS Admin"]]},
					fields=["role", *rights],
				)
			}
			if "Auri PMS Manager" in perms:
				self.assertIn("Auri PMS Admin", perms, doctype)
				for right in rights:
					self.assertGreaterEqual(
						perms["Auri PMS Admin"][right], perms["Auri PMS Manager"][right], f"{doctype} {right}"
					)
