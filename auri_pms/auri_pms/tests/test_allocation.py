"""Allocation vs utilisation of a project's team, and the project hours budget."""

import frappe

from auri_pms.auri_pms import api
from auri_pms.auri_pms.allocation import project_allocation, team_capacity
from auri_pms.auri_pms.health import get_health
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, REP, TM, TrackerTestCase, days_ago


class TestAllocation(TrackerTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.set_single_value(
			"PMS Settings",
			{
				"weekly_capacity_hours": 40,
				"utilisation_window_weeks": 4,
				"over_utilisation_pct": 110,
				"under_utilisation_pct": 50,
			},
		)

	def allocate(self, project, user, pct):
		row = frappe.db.get_value("Project Member", {"parent": project, "user": user}, "name")
		frappe.db.set_value("Project Member", row, "allocation_pct", pct)

	def log(self, user, hours, days):
		for n in days:
			self.logged_time(user, project=self.ALP, hours=hours, date=days_ago(n))

	def member(self, data, user):
		return next(m for m in data["members"] if m["user"] == user)

	def test_utilisation_is_logged_hours_per_week_against_allocated_hours(self):
		"""50% of a 40 h week is 20 h/week; 80 h over the 4-week window is 20 h/week, so 100%."""
		self.allocate(self.ALP, DEV, 50)
		self.log(DEV, 10, range(1, 9))
		dev = self.member(project_allocation(self.ALP), DEV)
		self.assertEqual((dev["allocated_week"], dev["logged_week"]), (20, 20))
		self.assertEqual((dev["utilisation_pct"], dev["state"]), (100, "ok"))

	def test_over_under_and_not_allocated(self):
		"""Above the over limit is over-used, below the under limit is under-used, no allocation is none."""
		self.allocate(self.ALP, DEV, 25)  # 10 h/week
		self.allocate(self.ALP, MGR, 50)  # 20 h/week
		self.log(DEV, 10, range(1, 6))  # 50 h -> 12.5 h/week -> 125%
		self.log(MGR, 8, range(1, 5))  # 32 h -> 8 h/week -> 40%
		self.log(REP, 2, [1])
		data = project_allocation(self.ALP)
		self.assertEqual(self.member(data, DEV)["state"], "over")
		self.assertEqual(self.member(data, MGR)["state"], "under")
		self.assertEqual(
			(self.member(data, REP)["utilisation_pct"], self.member(data, REP)["state"]), (None, "none")
		)
		self.assertEqual((data["allocated_week"], data["logged_week"]), (30, 21))

	def test_time_outside_the_window_is_not_counted(self):
		self.allocate(self.ALP, DEV, 50)
		self.log(DEV, 10, [40])
		self.assertEqual(self.member(project_allocation(self.ALP), DEV)["logged_week"], 0)

	def test_team_capacity_splits_allocation_by_project(self):
		"""60% on Alpha plus 50% on Beta is 110% of the person's week: over-allocated."""
		bet = frappe.get_doc("Project", self.BET)
		bet.append("tracker_members", {"user": DEV, "project_role": "Developer", "allocation_pct": 50})
		bet.save(ignore_permissions=True)
		self.allocate(self.ALP, DEV, 60)
		cap = team_capacity({self.ALP: "Alpha", self.BET: "Beta"})
		dev = next(p for p in cap["people"] if p["user"] == DEV)
		self.assertEqual(dev["total_pct"], 110)
		self.assertEqual([(p["label"], p["pct"]) for p in dev["projects"]], [("Alpha", 60), ("Beta", 50)])
		self.assertTrue(dev["over_allocated"])
		self.assertEqual(cap["over_allocated"], 1)

	def test_team_capacity_counts_only_the_given_projects(self):
		"""A project the viewer cannot see adds neither allocation nor hours."""
		bet = frappe.get_doc("Project", self.BET)
		bet.append("tracker_members", {"user": DEV, "project_role": "Developer", "allocation_pct": 50})
		bet.save(ignore_permissions=True)
		self.allocate(self.ALP, DEV, 60)
		dev = next(p for p in team_capacity({self.ALP: "Alpha"})["people"] if p["user"] == DEV)
		self.assertEqual((dev["total_pct"], dev["over_allocated"]), (60, False))

	def test_burnout_when_logged_hours_pass_the_limit_of_the_week(self):
		"""More than 110% of a 40 h week (44 h) on average is a burnout risk."""
		self.allocate(self.ALP, DEV, 100)
		self.log(DEV, 12, range(1, 16))  # 180 h over 4 weeks = 45 h/week
		dev = next(p for p in team_capacity({self.ALP: "Alpha"})["people"] if p["user"] == DEV)
		self.assertTrue(dev["burnout"])

	def test_portfolio_shows_team_capacity(self):
		self.allocate(self.ALP, DEV, 40)
		with self.as_user(MGR):
			people = api.get_portfolio().capacity["people"]
		self.assertIn(DEV, [p["user"] for p in people])

	def test_budget_replaces_the_estimate_for_hours_used(self):
		"""With a budget, burn is spent hours against the budget, not the ticket estimates."""
		self.new_item(MGR, estimated_hours=100)
		self.logged_time(DEV, project=self.ALP, hours=5)
		self.assertEqual(get_health(self.ALP).time.burn_pct, 5)
		frappe.db.set_value("Project", self.ALP, "pms_budget_hours", 10)
		self.assertEqual(get_health(self.ALP).time.burn_pct, 50)
		with self.as_user(MGR):
			self.assertEqual(api.get_project_hub(self.ALP).numbers["hours_budget"], 10)

	def test_a_removed_member_is_not_listed(self):
		"""Time logged by someone who has left the team is reported only as a total, not as a person."""
		self.allocate(self.ALP, DEV, 50)
		self.log(DEV, 10, range(1, 5))
		frappe.db.delete("Project Member", {"parent": self.ALP, "user": DEV})
		data = project_allocation(self.ALP)
		self.assertNotIn(DEV, [m["user"] for m in data["members"]])
		self.assertEqual((data["former_logged_week"], data["logged_week"]), (10, 0))

	def test_settings_saved_as_zero_fall_back_to_the_defaults(self):
		frappe.db.set_single_value(
			"PMS Settings",
			{"utilisation_window_weeks": 0, "over_utilisation_pct": 0, "under_utilisation_pct": 0},
		)
		data = project_allocation(self.ALP)
		self.assertEqual((data["weeks"], data["over_pct"], data["under_pct"]), (4, 110, 50))

	def test_weekly_hours_fall_in_their_week(self):
		self.allocate(self.ALP, DEV, 50)
		self.log(DEV, 6, [0, 1, 8])
		self.assertEqual(self.member(project_allocation(self.ALP), DEV)["weekly"], [0, 0, 6, 12])

	def test_team_capacity_lists_every_member_of_a_project_and_nobody_else(self):
		"""A member without allocation or hours is listed with the projects they belong to; someone who only logged time is not."""
		cap = team_capacity({self.ALP: "Alpha"})
		people = {p["user"]: p for p in cap["people"]}
		self.assertEqual(
			set(people), {MGR, DEV, REP}
		)  # the members of Alpha; the disabled member is left out
		self.assertEqual(people[REP]["member_of"], [self.ALP])
		self.assertEqual(people[REP]["total_pct"], 0)
		self.logged_time(
			TM, project=self.ALP, hours=2, entry_user=OUT
		)  # logged by an admin for someone who is not a member
		self.assertNotIn(OUT, [p["user"] for p in team_capacity({self.ALP: "Alpha"})["people"]])
