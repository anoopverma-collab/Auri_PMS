"""Project Hub API: project picker and per-project data."""

import frappe
from frappe.utils import add_days, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, REP, TM, TrackerTestCase


class TestProjectHub(TrackerTestCase):
	def hub_projects(self, user):
		with self.as_user(user):
			return {p.name: p for p in api.get_hub_projects()}

	def hub(self, user, project=None):
		with self.as_user(user):
			return api.get_project_hub(project or self.ALP)

	def test_picker_lists_only_projects_the_user_can_see(self):
		"""Members see their projects and public ones; outsiders only public ones; managers all."""
		self.assertTrue({self.ALP, self.BET} <= set(self.hub_projects(DEV)))
		out = self.hub_projects(OUT)
		self.assertIn(self.BET, out)
		self.assertNotIn(self.ALP, out)
		self.assertTrue({self.ALP, self.BET, self.GAM} <= set(self.hub_projects(TM)))
		self.assertIsNone(self.hub_projects(TM)[self.GAM].tracker_identifier)  # picker can flag it

	def test_picker_numbers(self):
		"""Open, overdue, mine, team size and the active sprint are shown on the card."""
		self.new_item(MGR, assigned_to=DEV, due_date=add_days(today(), -2))
		self.new_item(MGR, tracker="Task", assigned_to=MGR)
		closed = self.new_item(MGR, tracker="Task")
		self.save_as(MGR, closed, status="Closed")
		with self.as_user(MGR):
			sprint = frappe.get_doc(
				{
					"doctype": "Sprint",
					"sprint_name": "S1",
					"project": self.ALP,
					"start_date": today(),
					"end_date": add_days(today(), 13),
					"status": "Active",
				}
			).insert()
		card = self.hub_projects(DEV)[self.ALP]
		self.assertEqual((card.open, card.overdue, card.mine, card.members), (2, 1, 1, 4))
		self.assertEqual(card.active_sprint.name, sprint.name)

	def test_project_numbers_and_breakdowns(self):
		"""The project page counts open/overdue/unassigned/mine items, hours and breakdowns."""
		self.new_item(MGR, assigned_to=DEV, due_date=add_days(today(), -1), priority="High")
		second = self.new_item(MGR, tracker="Task")
		done = self.new_item(MGR, tracker="Task")
		self.save_as(MGR, done, status="Closed")
		self.logged_time(DEV, second.name, 3)
		data = self.hub(DEV)
		self.assertEqual(
			{
				k: data.numbers[k]
				for k in (
					"total",
					"open",
					"closed",
					"overdue",
					"unassigned",
					"mine",
					"hours_total",
					"hours_mine",
				)
			},
			{
				"total": 3,
				"open": 2,
				"closed": 1,
				"overdue": 1,
				"unassigned": 1,
				"mine": 1,
				"hours_total": 3,
				"hours_mine": 3,
			},
		)
		self.assertEqual({r["label"]: r["count"] for r in data.by_tracker}, {"Bug": 1, "Task": 1})
		self.assertEqual(data.backlog_items, 2)
		self.assertEqual(len(data.recent_items), 3)

	def test_access_check(self):
		"""An outsider cannot open a private project but can open a public one."""
		self.assertRaises(frappe.PermissionError, self.hub, OUT, self.ALP)
		self.assertEqual(self.hub(OUT, self.BET)["project"].tracker_identifier, "BET")

	def test_capabilities_follow_the_project_role(self):
		"""The page receives the user's capabilities so it only offers what they may do."""
		self.assertTrue(self.hub(MGR)["capabilities"]["can_manage_releases"])
		rep = self.hub(REP)["capabilities"]
		self.assertTrue(rep["can_create_items"])
		self.assertFalse(rep["can_manage_releases"] or rep["can_log_time"])
		self.assertTrue(
			self.hub(OUT, self.BET)["capabilities"]["can_create_items"]
		)  # public project, Reporter

	def test_active_sprint_burndown_and_lists(self):
		"""Active sprint comes with its burndown; sprints, releases and members are listed."""
		with self.as_user(MGR):
			frappe.get_doc(
				{
					"doctype": "Sprint",
					"sprint_name": "S1",
					"project": self.ALP,
					"start_date": add_days(today(), -3),
					"end_date": add_days(today(), 10),
					"status": "Active",
				}
			).insert()
		self.new_item(MGR, estimated_hours=4, sprint="ALP-S1")
		data = self.hub(DEV)
		self.assertEqual(data.active_sprint.name, "ALP-S1")
		self.assertEqual(data.active_sprint.burndown["unit"], "hours")
		self.assertEqual(len(data.active_sprint.burndown["rows"]), 4)  # start .. today
		self.assertEqual({r.name for r in data.releases}, set(self.world.releases.values()))
		self.assertEqual({m.user for m in data.members}, {MGR, DEV, REP, "gone@test.com"})
