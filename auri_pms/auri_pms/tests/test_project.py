"""Project extension rules (T-010 .. T-017)."""

import frappe

from auri_pms.auri_pms import api
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TrackerTestCase, ensure_company, make_user


class TestProject(TrackerTestCase):
	def project(self, name="Scratch", identifier=None, members=None, **kw):
		return frappe.get_doc(
			{
				"doctype": "Project",
				"company": ensure_company(),
				"project_name": name,
				"pms_enabled": 1 if identifier else 0,
				"tracker_identifier": identifier,
				"tracker_members": [{"user": u, "project_role": r} for u, r in (members or [])],
				**kw,
			}
		)

	def test_t010_invalid_identifiers_rejected(self):
		"""T-010: alp, A, 1AB, ABCDEFGHIJK are each rejected."""
		for bad in ("alp", "A", "1AB", "ABCDEFGHIJK"):
			self.assertThrows(
				"Identifier must be 2-10 uppercase letters", self.project(identifier=bad).insert
			)

	def test_t011_identifier_unique(self):
		"""T-011: ALP2 saves next to ALP; a second ALP is rejected."""
		self.project("Second", "ALP2").insert()
		self.assertThrows("Identifier ALP is already used by Project", self.project("Third", "ALP").insert)

	def test_t012_identifier_set_only_once(self):
		"""T-012: the identifier cannot change after it is set."""
		doc = frappe.get_doc("Project", self.ALP)
		doc.tracker_identifier = "ALPX"
		self.assertThrows("Value cannot be changed", doc.save)

	def test_t013_member_gains_tracker_user(self):
		"""T-013: a member without a tracker role gets Tracker User and a message."""
		make_user("plain@test.com", ())
		frappe.local.message_log = []
		doc = frappe.get_doc("Project", self.BET)
		doc.append("tracker_members", {"user": "plain@test.com", "project_role": "Reporter"})
		doc.save()
		self.assertIn("Tracker User", frappe.get_roles("plain@test.com"))
		self.assertTrue(any("plain@test.com" in str(m) for m in frappe.local.message_log))

	def test_t014_non_manager_cannot_edit_members(self):
		"""T-014: a developer cannot edit ALP members."""
		with self.as_user(DEV):
			doc = frappe.get_doc("Project", self.ALP)
			doc.append("tracker_members", {"user": OUT, "project_role": "Reporter"})
			self.assertThrows("You are not allowed to change members", doc.save)

	def test_t014b_project_manager_can_edit_members(self):
		"""A member with can_manage_members may change members."""
		with self.as_user(MGR):
			doc = frappe.get_doc("Project", self.ALP)
			doc.append("tracker_members", {"user": OUT, "project_role": "Reporter"})
			doc.save()
		self.assertTrue(frappe.db.exists("Project Member", {"parent": self.ALP, "user": OUT}))

	def test_t015_last_manager_cannot_be_removed(self):
		"""T-015: removing the only Manager member is rejected."""
		doc = frappe.get_doc("Project", self.BET)
		doc.tracker_members = []
		doc.append("tracker_members", {"user": DEV, "project_role": "Developer"})
		self.assertThrows("at least one member with a Manager role", doc.save)

	def test_t016_parent_project_self_or_cycle(self):
		"""T-016: parent = self, or A -> B -> A, is rejected."""
		a = frappe.get_doc("Project", self.ALP)
		a.parent_project = a.name
		self.assertThrows("cannot be the project itself", a.save)
		a.reload()
		a.parent_project = self.BET
		a.save()
		b = frappe.get_doc("Project", self.BET)
		b.parent_project = self.ALP
		self.assertThrows("would create a cycle", b.save)

	def test_t017_duplicate_member_rejected(self):
		"""T-017: the same user twice in members is rejected."""
		doc = frappe.get_doc("Project", self.BET)
		doc.append("tracker_members", {"user": MGR, "project_role": "Manager"})
		self.assertThrows("added more than once", doc.save)

	def test_enable_needs_identifier(self):
		"""Enable Auri PMS without an identifier is rejected."""
		doc = self.project("No ident")
		doc.pms_enabled = 1
		self.assertThrows("Set an Identifier to enable Auri PMS", doc.insert)

	def test_enabling_selects_all_active_ticket_types(self):
		"""A project that is enabled without choosing ticket types gets every active one."""
		doc = self.project("Defaults", "DEFT").insert()
		active = set(frappe.get_all("Ticket Type", filters={"is_active": 1}, pluck="name"))
		self.assertTrue(active)
		self.assertEqual({r.tracker for r in doc.enabled_trackers}, active)

	def test_chosen_ticket_types_are_kept(self):
		"""Ticket types chosen by hand are not replaced by the default."""
		doc = self.project("Chosen", "CHOS", enabled_trackers=[{"tracker": "Bug"}]).insert()
		self.assertEqual([r.tracker for r in doc.enabled_trackers], ["Bug"])

	def test_cannot_disable_with_records(self):
		"""Auri PMS cannot be switched off while the project has work items."""
		doc = frappe.get_doc("Project", self.ALP)
		doc.pms_enabled = 0
		self.assertThrows("cannot be disabled", doc.save)

	def test_disabled_project_is_hidden_and_unusable(self):
		"""A project without Enable Auri PMS is not listed and no work item can be created in it."""
		doc = self.project("Plain").insert()
		self.assertFalse(doc.pms_enabled)
		with self.as_user(MGR):
			self.assertNotIn(
				doc.name, [r[0] for r in api.project_create_query("Project", "", "name", 0, 50, None)]
			)
			self.assertNotIn(doc.name, [p.name for p in api.get_hub_projects()])
		self.assertThrows("Enable Auri PMS on Project", lambda: self.new_item(MGR, project=doc.name))
