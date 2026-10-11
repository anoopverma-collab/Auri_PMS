"""Sprints (SP-01 .. SP-22): planning, lifecycle, roll-ups, carry-over, visibility, burndown."""

import json

import frappe
from frappe.desk.query_report import run as run_report
from frappe.utils import add_days, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TM, TrackerTestCase
from auri_pms.auri_pms.utils import get_burndown


def day(offset: int) -> str:
	return add_days(today(), offset)


class TestSprint(TrackerTestCase):
	def sprint(self, name="Sprint 1", start=0, end=13, user=MGR, project=None, **kw):
		with self.as_user(user):
			return frappe.get_doc(
				{
					"doctype": "Sprint",
					"sprint_name": name,
					"project": project or self.ALP,
					"start_date": day(start),
					"end_date": day(end),
					**kw,
				}
			).insert()

	def values(self, name, *fields, doctype="Sprint"):
		return frappe.db.get_value(doctype, name, list(fields), as_dict=True)

	def test_sp01_manager_creates_developer_cannot(self):
		"""SP-01: only users with can_manage_releases create sprints; the name is <identifier>-<sprint>."""
		self.assertThrows("You are not allowed to manage sprints in Project", lambda: self.sprint(user=DEV))
		self.assertEqual(self.sprint().name, "ALP-Sprint 1")

	def test_sp02_end_before_start(self):
		"""SP-02: End Date cannot be before Start Date."""
		self.assertThrows("End Date cannot be before Start Date", lambda: self.sprint(start=5, end=2))

	def test_sp03_overlap_and_adjacent(self):
		"""SP-03: overlapping sprints are rejected; back-to-back sprints are fine."""
		first = self.sprint("S1", 0, 13)
		self.assertThrows(
			f"Sprint {first.name} already covers these dates", lambda: self.sprint("S2", 13, 20)
		)
		self.assertTrue(self.sprint("S2", 14, 27).name)

	def test_sp04_project_needs_identifier(self):
		"""SP-04: a project without identifier cannot have sprints."""
		self.assertThrows("Enable Auri PMS on Project", lambda: self.sprint(project=self.GAM, user=TM))

	def test_sp05_lifecycle(self):
		"""SP-05: Planned -> Active -> Completed only; no skipping, no going back."""
		sprint = self.sprint()
		self.assertThrows(
			"Start the sprint before completing it", lambda: self.save_as(MGR, sprint, status="Completed")
		)
		sprint.reload()
		self.save_as(MGR, sprint, status="Active")
		self.assertThrows("cannot move back to Planned", lambda: self.save_as(MGR, sprint, status="Planned"))
		sprint.reload()
		self.save_as(MGR, sprint, status="Completed")
		self.assertEqual(frappe.db.get_value("Sprint", sprint.name, "status"), "Completed")

	def test_sp06_one_active_sprint_per_project(self):
		"""SP-06: a second Active sprint in a project is rejected; another project is independent."""
		active = self.sprint("A", 0, 13, status="Active")
		self.assertThrows(
			f"Sprint {active.name} is already active", lambda: self.sprint("B", 14, 27, status="Active")
		)
		self.assertEqual(self.sprint("C", 0, 13, project=self.BET, status="Active").status, "Active")

	def test_sp07_completed_sprint_is_locked(self):
		"""SP-07: a Completed sprint keeps its dates and goal."""
		sprint = self.sprint(status="Active")
		self.save_as(MGR, sprint, status="Completed")
		sprint.reload()
		self.assertThrows(
			"Completed sprints cannot be changed", lambda: self.save_as(MGR, sprint, end_date=day(20))
		)

	def test_sp08_item_must_share_the_project(self):
		"""SP-08: an item joins a sprint of its own project only."""
		sprint = self.sprint()
		self.assertEqual(self.new_item(MGR, sprint=sprint.name).sprint, sprint.name)
		self.assertThrows(
			"does not belong to Project", lambda: self.new_item(MGR, self.BET, sprint=sprint.name)
		)

	def test_sp09_completed_sprint_takes_no_new_items(self):
		"""SP-09: Completed sprints reject new items; an existing member can still be saved."""
		sprint = self.sprint(status="Active")
		item = self.new_item(MGR, sprint=sprint.name)
		self.save_as(MGR, sprint, status="Completed", carry_over_to=None)
		sprint.reload()
		self.assertThrows(
			"only Planned or Active sprints accept work items", lambda: self.new_item(MGR, sprint=sprint.name)
		)
		self.assertFalse(
			frappe.db.get_value("Work Item", item.name, "sprint")
		)  # open item went to the backlog

	def test_sp10_rollups(self):
		"""SP-10: items, closed items, % complete, estimated and spent hours roll up into the sprint."""
		sprint = self.sprint()
		items = [self.new_item(MGR, tracker="Task", sprint=sprint.name, estimated_hours=4) for _ in range(4)]
		self.save_as(MGR, items[0], status="Closed")
		self.logged_time(DEV, items[1].name, 3)
		self.assertEqual(
			self.values(
				sprint.name,
				"total_items",
				"closed_items",
				"percent_complete",
				"estimated_hours",
				"spent_hours",
			),
			{
				"total_items": 4,
				"closed_items": 1,
				"percent_complete": 25,
				"estimated_hours": 16,
				"spent_hours": 3,
			},
		)

	def test_sp11_moving_an_item_updates_both_sprints(self):
		"""SP-11: moving an item between sprints recalculates both."""
		first, second = self.sprint("S1", 0, 13), self.sprint("S2", 14, 27)
		item = self.new_item(MGR, sprint=first.name)
		self.new_item(MGR, sprint=first.name)
		self.save_as(MGR, item, sprint=second.name)
		self.assertEqual(self.values(first.name, "total_items").total_items, 1)
		self.assertEqual(self.values(second.name, "total_items").total_items, 1)

	def test_sp12_deleting_an_item_updates_the_sprint(self):
		"""SP-12: deleting an item recalculates its sprint."""
		sprint = self.sprint()
		item = self.new_item(MGR, sprint=sprint.name)
		with self.as_user(MGR):
			frappe.delete_doc("Work Item", item.name)
		self.assertEqual(self.values(sprint.name, "total_items").total_items, 0)

	def test_sp13_complete_with_carry_over(self):
		"""SP-13: completing moves unfinished items to the chosen sprint and keeps closed ones."""
		first, second = self.sprint("S1", 0, 13, status="Active"), self.sprint("S2", 14, 27)
		done = self.new_item(MGR, tracker="Task", sprint=first.name)
		open_item = self.new_item(MGR, tracker="Task", sprint=first.name)
		self.save_as(MGR, done, status="Closed")
		first.reload()
		self.save_as(MGR, first, status="Completed", carry_over_to=second.name)
		self.assertEqual(frappe.db.get_value("Work Item", open_item.name, "sprint"), second.name)
		self.assertEqual(frappe.db.get_value("Work Item", done.name, "sprint"), first.name)
		self.assertEqual(
			self.values(first.name, "total_items", "closed_items", "percent_complete"),
			{"total_items": 1, "closed_items": 1, "percent_complete": 100},
		)
		self.assertEqual(self.values(second.name, "total_items").total_items, 1)

	def test_sp14_complete_without_target_goes_to_backlog(self):
		"""SP-14: with no target the unfinished items return to the backlog."""
		sprint = self.sprint(status="Active")
		item = self.new_item(MGR, sprint=sprint.name)
		self.save_as(MGR, sprint, status="Completed")
		self.assertFalse(frappe.db.get_value("Work Item", item.name, "sprint"))

	def test_sp15_carry_over_target_rules(self):
		"""SP-15: the target must be another open sprint of the same project."""
		sprint = self.sprint(status="Active")
		other_project = self.sprint("B1", 0, 13, project=self.BET)
		for target in (sprint.name, other_project.name):
			sprint.reload()
			self.assertThrows(
				"must be another Planned or Active sprint",
				lambda target=target: self.save_as(MGR, sprint, status="Completed", carry_over_to=target),
			)

	def test_sp16_delete_rules(self):
		"""SP-16: a sprint with items cannot be deleted; Tracker Users cannot delete sprints at all."""
		sprint = self.sprint()
		self.new_item(MGR, sprint=sprint.name)
		with self.as_user(TM):
			self.assertRaises(frappe.LinkExistsError, frappe.delete_doc, "Sprint", sprint.name)
		with self.as_user(DEV):
			self.assertRaises(frappe.PermissionError, frappe.delete_doc, "Sprint", sprint.name)

	def test_sp17_visibility(self):
		"""SP-17: outsiders see sprints of public projects only."""
		private, public = self.sprint("P1", 0, 13), self.sprint("B1", 0, 13, project=self.BET)
		with self.as_user(OUT):
			names = set(frappe.get_list("Sprint", pluck="name", limit_page_length=0))
		self.assertIn(public.name, names)
		self.assertNotIn(private.name, names)
		self.assertFalse(frappe.has_permission("Sprint", "read", doc=private.name, user=OUT))

	def test_sp18_bulk_move_api(self):
		"""SP-18: move_to_sprint moves what it can and reports the rest without popups."""
		sprint = self.sprint()
		ok_one, ok_two = self.new_item(MGR), self.new_item(MGR)
		foreign = self.new_item(MGR, self.BET)
		with self.as_user(MGR):
			result = api.move_to_sprint([ok_one.name, foreign.name, ok_two.name], sprint.name)
		self.assertEqual(result["moved"], 2)
		self.assertEqual([f["name"] for f in result["failed"]], [foreign.name])
		self.assertIn("does not belong to Project", result["failed"][0]["error"])
		self.assertEqual(self.values(sprint.name, "total_items").total_items, 2)
		with self.as_user(MGR):
			api.move_to_sprint([ok_one.name], None)  # back to the backlog
		self.assertEqual(self.values(sprint.name, "total_items").total_items, 1)

	def test_sp19_parent_and_child_in_a_sprint(self):
		"""SP-19: parent and child tickets can sit in the same or different sprints; each counts on its own."""
		first, second = self.sprint("S1", 0, 13), self.sprint("S2", 14, 27)
		parent = self.new_item(MGR, tracker="Task", sprint=first.name)
		self.new_item(MGR, tracker="Task", parent_work_item=parent.name, sprint=first.name)
		self.new_item(MGR, tracker="Task", parent_work_item=parent.name, sprint=second.name)
		self.assertEqual(self.values(first.name, "total_items").total_items, 2)
		self.assertEqual(self.values(second.name, "total_items").total_items, 1)

	def test_sp20_burndown(self):
		"""SP-20: ideal falls linearly, actual drops when items close and stops at today."""
		sprint = self.sprint("S1", -4, 5, status="Active")
		first = self.new_item(MGR, tracker="Task", sprint=sprint.name, estimated_hours=4)
		self.new_item(MGR, tracker="Task", sprint=sprint.name, estimated_hours=6)
		self.save_as(MGR, first, status="Closed")
		frappe.db.set_value(
			"Work Item", first.name, "closed_on", f"{day(-3)} 10:00:00", update_modified=False
		)
		burndown = get_burndown(sprint.name)
		rows = {str(r["date"]): r for r in burndown["rows"]}
		self.assertEqual((burndown["unit"], burndown["total"]), ("hours", 10))
		self.assertEqual(rows[day(-4)]["actual"], 10)
		self.assertEqual((rows[day(-3)]["actual"], rows[day(-3)]["completed"]), (6, 4))
		self.assertEqual(rows[day(0)]["actual"], 6)
		self.assertIsNone(rows[day(1)]["actual"])
		self.assertEqual((rows[day(-4)]["ideal"], rows[day(5)]["ideal"]), (10, 0))

	def test_sp21_reports_respect_visibility(self):
		"""SP-21: Sprint Summary hides private sprints; Sprint Burndown refuses them."""
		sprint = self.sprint(status="Active")
		self.new_item(MGR, sprint=sprint.name)
		with self.as_user(TM):
			self.assertIn(sprint.name, json.dumps(run_report("Sprint Summary", {})["result"], default=str))
			self.assertTrue(run_report("Sprint Burndown", {"sprint": sprint.name})["result"])
		with self.as_user(OUT):
			self.assertNotIn(sprint.name, json.dumps(run_report("Sprint Summary", {})["result"], default=str))
			self.assertRaises(frappe.PermissionError, run_report, "Sprint Burndown", {"sprint": sprint.name})

	def test_sp22_removing_the_last_open_sprint_keeps_items(self):
		"""SP-22: items keep every other field when they leave a sprint."""
		sprint = self.sprint(status="Active")
		item = self.new_item(MGR, sprint=sprint.name, subject="Keep me", priority="High")
		self.save_as(MGR, sprint, status="Completed")
		item.reload()
		self.assertEqual((item.subject, item.priority, item.sprint), ("Keep me", "High", None))
