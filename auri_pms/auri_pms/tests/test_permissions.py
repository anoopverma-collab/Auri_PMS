"""Visibility rules (T-110 .. T-119)."""

import json

import frappe
from frappe.desk.query_report import run as run_report
from frappe.desk.search import search_link

from auri_pms.auri_pms.tests.utils import (
	DEV,
	MGR,
	OUT,
	REP,
	TM,
	TrackerTestCase,
	days_ago,
	ensure_company,
)


class TestPermissions(TrackerTestCase):
	def setUp(self):
		super().setUp()
		self.alp_item = self.new_item(MGR, subject="Alpha secret")
		self.bet_item = self.new_item(MGR, self.BET, subject="Beta public")

	def names(self, user, doctype="Work Item"):
		with self.as_user(user):
			return set(frappe.get_list(doctype, pluck="name", limit_page_length=0))

	def created(self, *items):
		return {i.name for i in items}

	def test_t110_outsider_sees_only_public(self):
		"""T-110: out only sees BET items, read-only (checked on the items this test created, so other data may exist)."""
		visible = self.names(OUT)
		self.assertIn(self.bet_item.name, visible)
		self.assertNotIn(self.alp_item.name, visible)
		self.assertFalse(frappe.has_permission("Work Item", "write", doc=self.bet_item.name, user=OUT))

	def test_t111_member_sees_alp_and_bet(self):
		"""T-111: dev sees ALP (member) and BET (public, read-only) items."""
		self.assertTrue(self.created(self.alp_item, self.bet_item) <= self.names(DEV))

	def test_t112_manager_sees_all(self):
		"""T-112: tm sees everything."""
		self.assertTrue(self.created(self.alp_item, self.bet_item) <= self.names(TM))
		self.assertEqual(self.names(TM), set(frappe.get_all("Work Item", pluck="name")))

	def test_t113_outsider_cannot_open_private_item(self):
		"""T-113: has_permission is False and opening the document raises PermissionError."""
		self.assertFalse(frappe.has_permission("Work Item", "read", doc=self.alp_item.name, user=OUT))
		with self.as_user(OUT):
			self.assertRaises(
				frappe.PermissionError,
				frappe.get_doc("Work Item", self.alp_item.name).check_permission,
				"read",
			)

	def test_t114_link_search_respects_visibility(self):
		"""T-114: search_link as out returns no ALP items."""
		with self.as_user(OUT):
			values = {r["value"] for r in search_link("Work Item", "")}
		self.assertIn(self.bet_item.name, values)
		self.assertNotIn(self.alp_item.name, values)

	def test_t115_time_entries_and_releases(self):
		"""T-115: get_list on Time Entry and Release as out returns only BET records."""
		self.logged_time(MGR, None, 1, project=self.ALP)
		bet_entry = self.logged_time(MGR, None, 1, project=self.BET)
		bet_release = frappe.get_doc(
			{"doctype": "Release", "release_name": "b1", "project": self.BET}
		).insert()
		time_entries, releases = self.names(OUT, "Time Entry"), self.names(OUT, "Release")
		self.assertIn(bet_entry.name, time_entries)
		self.assertIn(bet_release.name, releases)
		self.assertFalse(
			frappe.get_all("Time Entry", {"name": ["in", list(time_entries)], "project": self.ALP})
		)
		self.assertFalse(frappe.get_all("Release", {"name": ["in", list(releases)], "project": self.ALP}))

	def test_t116_parent_membership_does_not_grant_child_access(self):
		"""T-116: membership of a parent project gives no access to its child project."""
		parent = frappe.get_doc(
			{
				"doctype": "Project",
				"company": ensure_company(),
				"project_name": "Parent",
				"pms_enabled": 1,
				"tracker_identifier": "PAR",
				"tracker_members": [
					{"user": OUT, "project_role": "Developer"},
					{"user": MGR, "project_role": "Manager"},
				],
			}
		).insert()
		child = frappe.get_doc(
			{
				"doctype": "Project",
				"company": ensure_company(),
				"project_name": "Child",
				"pms_enabled": 1,
				"tracker_identifier": "CHD",
				"parent_project": parent.name,
				"tracker_members": [{"user": MGR, "project_role": "Manager"}],
			}
		).insert()
		child_item = self.new_item(MGR, child.name)
		self.assertNotIn(child_item.name, self.names(OUT))

	def test_t117_disabled_user_loses_access(self):
		"""T-117: after disabling dev, get_list returns nothing."""
		self.assertIn(self.alp_item.name, self.names(DEV))
		frappe.db.set_value("User", DEV, "enabled", 0)
		from auri_pms.auri_pms.utils import clear_cache

		clear_cache()
		self.assertEqual(self.names(DEV), set())

	def test_t118_deleting_items(self):
		"""T-118: rep, items with time or children are refused; a clean item is deleted and its ToDos closed."""
		own = self.new_item(REP)
		with self.as_user(REP):
			self.assertRaises(frappe.ValidationError, frappe.delete_doc, "Work Item", own.name)
		with_time = self.new_item(MGR)
		self.logged_time(DEV, with_time.name, 1)
		parent = self.new_item(MGR)
		self.new_item(MGR, parent_work_item=parent.name)
		clean = self.new_item(MGR, assigned_to=DEV)
		with self.as_user(MGR):
			self.assertRaises(frappe.ValidationError, frappe.delete_doc, "Work Item", with_time.name)
			self.assertRaises(frappe.ValidationError, frappe.delete_doc, "Work Item", parent.name)
			frappe.delete_doc("Work Item", clean.name)
		self.assertFalse(frappe.db.exists("Work Item", clean.name))
		self.assertFalse(frappe.db.exists("ToDo", {"reference_name": clean.name, "status": "Open"}))

	def test_t119_reports_respect_visibility(self):
		"""T-119: no script report shows ALP data to out."""
		self.new_item(MGR, due_date=days_ago(3), subject="Alpha overdue", release=self.world.releases["v1"])
		self.logged_time(MGR, None, 2, project=self.ALP)
		filters = {
			"Work Item Summary": {},
			"Time Log Summary": {"from_date": days_ago(7), "to_date": days_ago(-1), "group_by": "Project"},
			"Release Progress": {},
			"Overdue Work Items": {},
		}
		for report, report_filters in filters.items():
			with self.as_user(TM):
				visible = json.dumps(run_report(report, report_filters)["result"], default=str)
			self.assertIn(self.ALP, visible, f"{report} should show ALP to a manager")
			with self.as_user(OUT):
				hidden = json.dumps(run_report(report, report_filters)["result"], default=str)
			self.assertNotIn(self.ALP, hidden, report)


class TestAllocationOnly(TrackerTestCase):
	"""Only the people allocated to a project change its data; an Auri PMS Admin or System Manager may change any."""

	def test_a_non_member_cannot_change_a_work_item_of_a_public_project(self):
		item = self.new_item(MGR, self.BET)
		for ptype in ("write", "delete"):
			self.assertFalse(frappe.has_permission("Work Item", ptype, doc=item.name, user=OUT))
			self.assertFalse(frappe.has_permission("Work Item", ptype, doc=item.name, user=DEV))

	def test_a_member_can_change_the_work_items_of_their_project(self):
		item = self.new_item(MGR)
		self.assertTrue(frappe.has_permission("Work Item", "write", doc=item.name, user=MGR))

	def test_an_admin_can_change_any_project(self):
		item = self.new_item(MGR, self.BET)
		self.assertTrue(frappe.has_permission("Work Item", "write", doc=item.name, user=TM))

	def test_a_non_member_cannot_edit_the_project_itself(self):
		self.assertFalse(frappe.has_permission("Project", "write", doc=self.BET, user=OUT))
		self.assertFalse(frappe.has_permission("Project", "write", doc=self.BET, user=DEV))
		self.assertTrue(frappe.has_permission("Project", "write", doc=self.ALP, user=MGR))


class TestMembersSeeOnlyOwnWorkItems(TrackerTestCase):
	"""PMS Settings > Members See All Work Items: unticked, a member sees only the items assigned to them."""

	def setUp(self):
		super().setUp()
		self.mine = self.new_item(MGR, subject="Assigned to dev", assigned_to=DEV)
		self.extra = self.new_item(
			MGR, subject="Dev is an extra assignee", additional_assignees=[{"user": DEV}]
		)
		self.others = self.new_item(MGR, subject="Assigned to the manager", assigned_to=MGR)
		self.nobody = self.new_item(MGR, subject="Unassigned")

	def tearDown(self):
		frappe.db.set_single_value("PMS Settings", "members_see_all_work_items", 1)
		super().tearDown()

	def names(self, user):
		with self.as_user(user):
			return set(frappe.get_list("Work Item", pluck="name", limit_page_length=0))

	def created(self):
		return {i.name for i in (self.mine, self.extra, self.others, self.nobody)}

	def test_ticked_by_default_a_member_sees_every_item_of_their_project(self):
		self.assertEqual(frappe.get_meta("PMS Settings").get_field("members_see_all_work_items").default, "1")
		self.assertTrue(self.created() <= self.names(DEV))

	def test_a_site_that_never_saved_the_setting_keeps_members_seeing_everything(self):
		"""An update must not narrow what members see: an unsaved Check reads as 0, the stored row is what counts."""
		frappe.db.sql(
			"delete from `tabSingles` where doctype = 'PMS Settings' and field = 'members_see_all_work_items'"
		)
		frappe.clear_document_cache("PMS Settings", "PMS Settings")
		self.assertTrue(self.created() <= self.names(DEV))

	def test_unticked_a_member_sees_only_the_items_assigned_to_them(self):
		frappe.db.set_single_value("PMS Settings", "members_see_all_work_items", 0)
		seen = self.names(DEV) & self.created()
		self.assertEqual(seen, {self.mine.name, self.extra.name})

	def test_unticked_a_member_cannot_open_an_item_assigned_to_someone_else(self):
		frappe.db.set_single_value("PMS Settings", "members_see_all_work_items", 0)
		self.assertTrue(frappe.has_permission("Work Item", "read", doc=self.mine.name, user=DEV))
		self.assertTrue(frappe.has_permission("Work Item", "write", doc=self.extra.name, user=DEV))
		self.assertFalse(frappe.has_permission("Work Item", "read", doc=self.others.name, user=DEV))
		self.assertFalse(frappe.has_permission("Work Item", "read", doc=self.nobody.name, user=DEV))

	def test_unticked_a_manager_and_an_admin_still_see_everything(self):
		frappe.db.set_single_value("PMS Settings", "members_see_all_work_items", 0)
		self.assertTrue(self.created() <= self.names(MGR))  # Manager role: can manage members
		self.assertTrue(self.created() <= self.names(TM))  # Auri PMS Admin

	def test_unticked_a_public_project_stays_readable_for_a_non_member(self):
		frappe.db.set_single_value("PMS Settings", "members_see_all_work_items", 0)
		item = self.new_item(MGR, self.BET, subject="Public ticket")
		self.assertIn(item.name, self.names(OUT))

	def test_unticked_a_member_can_still_create_an_item(self):
		frappe.db.set_single_value("PMS Settings", "members_see_all_work_items", 0)
		item = self.new_item(DEV, subject="Raised by dev", assigned_to=DEV)
		self.assertIn(item.name, self.names(DEV))
