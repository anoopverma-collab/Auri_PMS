"""Delivery & Health: projects, releases, sprints, tasks, workload and delivery health."""

import frappe
from frappe.desk.search import search_link
from frappe.utils import add_days, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TM, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestManagementDashboard(TrackerTestCase):
	def data(self, user=TM):
		with self.as_user(user):
			return api.get_management_dashboard()

	def row(self, rows, name, key="name"):
		return next(r for r in rows if r[key] == name)

	def release(self, name, due, status="Open"):
		with self.as_user(MGR):
			return frappe.get_doc(
				{"doctype": "Release", "release_name": name, "project": self.ALP, "due_date": due, "status": status}
			).insert()

	def test_only_admins_and_project_managers_get_it(self):
		for user in (DEV, OUT):
			with self.as_user(user), self.assertRaises(frappe.PermissionError):
				api.get_management_dashboard()
		self.assertIn(self.ALP, {p["name"] for p in self.data(MGR)["projects"]})
		self.assertTrue({self.ALP, self.BET} <= {p["name"] for p in self.data(TM)["projects"]})
		self.assertNotIn(self.GAM, {p["name"] for p in self.data(TM)["projects"]})  # Auri PMS is off there

	def test_task_counts(self):
		before = self.row(self.data()["projects"], self.ALP)
		self.new_item(MGR, due_date=days(-2))  # open and overdue
		self.new_item(MGR, status="In Progress")
		done = self.new_item(MGR, tracker="Task")
		self.save_as(MGR, done, status="Closed")
		after = self.row(self.data()["projects"], self.ALP)
		self.assertEqual(after["total"] - before["total"], 3)
		self.assertEqual(after["open"] - before["open"], 2)
		self.assertEqual(after["in_progress"] - before["in_progress"], 1)
		self.assertEqual(after["completed"] - before["completed"], 1)
		self.assertEqual(after["overdue"] - before["overdue"], 1)

	def test_an_overdue_release_delays_its_project(self):
		late = self.release("Late one", days(-5))
		self.new_item(MGR, release=late.name)
		data = self.data()
		row = self.row(data["releases"], late.name)
		self.assertTrue(row["late"])
		self.assertEqual(row["late_days"], 5)
		self.assertEqual(row["planned"], days(-5))
		self.assertIsNone(row["actual"])
		self.assertEqual(row["release_name"], "Late one")
		self.assertIn(late.name, {r["name"] for r in data["delayed_releases"]})
		project = self.row(data["projects"], self.ALP)
		self.assertTrue(project["delayed"])
		self.assertIn("overdue release", project["delay_reasons"])

	def test_a_closed_release_reports_when_it_really_finished(self):
		release = self.release("Finished late", days(-3))
		item = self.new_item(MGR, tracker="Task", release=release.name)
		self.save_as(MGR, item, status="Closed")
		self.save_as(MGR, release, status="Closed")
		row = self.row(self.data()["releases"], release.name)
		self.assertFalse(row["late"])  # closed, so no longer overdue
		self.assertEqual(row["actual"], today())
		self.assertEqual(row["late_days"], 3)

	def test_an_overdue_sprint_and_the_releases_of_its_tickets(self):
		release = self.release("Sprinted", days(30))
		with self.as_user(MGR):
			sprint = frappe.get_doc(
				{
					"doctype": "Sprint",
					"sprint_name": "Old sprint",
					"project": self.ALP,
					"start_date": days(-60),
					"end_date": days(-47),
				}
			).insert()
		self.new_item(MGR, release=release.name, sprint=sprint.name)
		data = self.data()
		row = self.row(data["sprints"], sprint.name)
		self.assertTrue(row["late"])
		self.assertEqual(row["releases"], ["Sprinted"])
		self.assertEqual(row["total"], 1)
		linked = self.row(data["releases"], release.name)
		self.assertEqual((linked["sprints_total"], linked["sprints_overdue"]), (1, 1))

	def test_workload_per_person_counts_assigned_and_additional(self):
		before = {u["user"]: u for u in self.data()["users"]}
		self.new_item(MGR, assigned_to=DEV, due_date=days(-1))
		self.new_item(MGR, assigned_to=MGR, additional_assignees=[{"user": DEV}])
		self.new_item(MGR)  # nobody
		after = {u["user"]: u for u in self.data()["users"]}
		base = before.get(DEV, {"assigned": 0, "pending": 0, "overdue": 0})
		self.assertEqual(after[DEV]["assigned"] - base["assigned"], 2)
		self.assertEqual(after[DEV]["pending"] - base["pending"], 2)
		self.assertEqual(after[DEV]["overdue"] - base["overdue"], 1)
		unassigned_before = before.get("", {"pending": 0})["pending"]
		self.assertEqual(after[""]["pending"] - unassigned_before, 1)

	def test_every_delivery_health_tile_has_the_records_behind_it(self):
		"""Each tile opens a list: the ids carry exactly the records that its count adds up."""
		self.release("R-late", days(-3))
		self.new_item(MGR, tracker="Task")  # unassigned
		data = self.data()
		self.assertEqual(len(data["ids"]["delayed_projects"]), data["kpis"]["delayed"])
		self.assertEqual(len(data["ids"]["delayed_releases"]), data["kpis"]["releases_overdue"])
		self.assertEqual(len(data["ids"]["overdue_sprints"]), data["kpis"]["sprints_overdue"])
		self.assertEqual(len(data["ids"]["pending"]), data["kpis"]["pending_activities"])
		self.assertIn(self.ALP, data["ids"]["delayed_projects"])
		self.assertTrue(data["ids"]["delayed_releases"])
		# the lists of those ids hold the same number of records the tile shows
		for doctype, key in (("Release", "delayed_releases"), ("Work Item", "pending")):
			with self.as_user(TM):
				found = frappe.get_list(doctype, filters={"name": ["in", data["ids"][key]]}, pluck="name")
			self.assertEqual(sorted(found), sorted(data["ids"][key]))

	def hours(self, project=None, **filters):
		with self.as_user(TM):
			data = api.get_management_dashboard(project=project, **filters)["hours"]
		return {r["name"]: r for r in data["projects"]}, data["total"]

	def test_hours_estimated_against_actual_and_billable(self):
		rows, _total = self.hours()
		before = rows[self.ALP]
		one = self.new_item(MGR, tracker="Task", estimated_hours=10)
		two = self.new_item(MGR, tracker="Task", estimated_hours=6)
		self.logged_time(MGR, work_item=one.name, hours=4, is_billable=1)
		self.logged_time(MGR, work_item=two.name, hours=2, is_billable=0)
		rows, total = self.hours()
		now = rows[self.ALP]
		self.assertEqual(now["estimated"] - before["estimated"], 16)
		self.assertEqual(now["actual"] - before["actual"], 6)
		self.assertEqual(now["billable"] - before["billable"], 4)
		self.assertEqual(now["variance"], round(now["actual"] - now["estimated"], 2))
		self.assertEqual(now["billable_pct"], round(now["billable"] * 100 / now["actual"], 1))
		for key in ("estimated", "actual", "billable"):  # the total is the sum of the projects
			self.assertEqual(total[key], round(sum(r[key] for r in rows.values()), 2), key)

	def test_a_project_with_no_time_has_no_billable_share(self):
		rows, _total = self.hours()
		self.assertEqual(rows[self.BET]["actual"], 0)
		self.assertIsNone(rows[self.BET]["billable_pct"])

	def test_the_hours_follow_the_filters(self):
		release = self.release("R-hours", days(10))
		inside = self.new_item(MGR, tracker="Task", estimated_hours=8, release=release.name)
		outside = self.new_item(MGR, tracker="Task", estimated_hours=5)
		self.logged_time(MGR, work_item=inside.name, hours=3, is_billable=1)
		self.logged_time(MGR, work_item=outside.name, hours=2, is_billable=1)
		rows, _total = self.hours(release=release.name, project=self.ALP)
		self.assertEqual(set(rows), {self.ALP})
		self.assertEqual((rows[self.ALP]["estimated"], rows[self.ALP]["actual"], rows[self.ALP]["billable"]), (8, 3, 3))
		rows, _total = self.hours(project=self.BET)
		self.assertEqual(set(rows), {self.BET})

	def test_pending_activities_are_unassigned_or_waiting_on_the_client(self):
		before = self.data()["kpis"]["pending_activities"]
		self.new_item(MGR, assigned_to=DEV)  # assigned and moving: not pending
		unassigned = self.new_item(MGR, subject="Nobody has it")
		after = self.data()
		self.assertEqual(after["kpis"]["pending_activities"] - before, 1)
		self.assertIn(unassigned.name, {t["name"] for t in after["pending"]})

	def test_upcoming_deadlines_cover_the_next_two_weeks(self):
		soon = self.new_item(MGR, due_date=days(5), subject="Due soon")
		far = self.new_item(MGR, due_date=days(40), subject="Due much later")
		names = {t["name"] for t in self.data()["upcoming"]["tasks"]}
		self.assertIn(soon.name, names)
		self.assertNotIn(far.name, names)


class TestManagementDashboardFilters(TrackerTestCase):
	"""Project, Release and Sprint filters: releases and sprints work project-wise, like everything else."""

	def setUp(self):
		super().setUp()
		self.alp_rel = self.make_release(self.ALP, "Alpha 1")
		self.alp_rel2 = self.make_release(self.ALP, "Alpha 2")
		self.bet_rel = self.make_release(self.BET, "Beta 1")
		self.alp_sprint = self.make_sprint(self.ALP, "Alpha sprint", -3, 10)
		self.bet_sprint = self.make_sprint(self.BET, "Beta sprint", -3, 10)
		# Alpha 1 in the Alpha sprint (1 open, 1 overdue); Alpha 2 outside any sprint; one Beta ticket
		self.new_item(MGR, release=self.alp_rel, sprint=self.alp_sprint, assigned_to=DEV, due_date=days(-1))
		self.new_item(MGR, release=self.alp_rel, sprint=self.alp_sprint, assigned_to=MGR)
		self.new_item(MGR, release=self.alp_rel2, assigned_to=DEV)
		self.new_item(MGR, self.BET, release=self.bet_rel, sprint=self.bet_sprint, assigned_to=MGR)

	def make_release(self, project, name):
		with self.as_user(MGR):
			return frappe.get_doc(
				{"doctype": "Release", "release_name": name, "project": project, "due_date": days(20)}
			).insert().name

	def make_sprint(self, project, name, start, end):
		with self.as_user(MGR):
			return frappe.get_doc(
				{
					"doctype": "Sprint",
					"sprint_name": name,
					"project": project,
					"start_date": days(start),
					"end_date": days(end),
				}
			).insert().name

	def data(self, user=TM, **filters):
		with self.as_user(user):
			return api.get_management_dashboard(**filters)

	def names(self, rows):
		return {r["name"] for r in rows}

	def test_without_filters_every_project_release_and_sprint_is_offered(self):
		options = self.data()["options"]
		self.assertTrue({self.alp_rel, self.alp_rel2, self.bet_rel} <= self.names(options["releases"]))
		self.assertTrue({self.alp_sprint, self.bet_sprint} <= self.names(options["sprints"]))
		self.assertTrue({self.ALP, self.BET} <= self.names(options["projects"]))

	def test_the_dropdowns_list_only_what_was_created_for_the_chosen_project(self):
		options = self.data(project=self.ALP)["options"]
		self.assertTrue({self.ALP, self.BET} <= self.names(options["projects"]))  # every project stays offered for the next pick
		self.assertTrue({self.alp_rel, self.alp_rel2} <= self.names(options["releases"]))
		self.assertNotIn(self.bet_rel, self.names(options["releases"]))
		self.assertIn(self.alp_sprint, self.names(options["sprints"]))
		self.assertNotIn(self.bet_sprint, self.names(options["sprints"]))
		self.assertTrue(all(r["project"] == self.ALP for r in options["releases"] + options["sprints"]))

	def test_the_link_field_dropdowns_are_project_wise_too(self):
		"""What the Release and Sprint Link fields on the page search: only the chosen project's records."""
		for doctype, mine, other in (("Release", self.alp_rel, self.bet_rel), ("Sprint", self.alp_sprint, self.bet_sprint)):
			with self.as_user(MGR):
				found = {r["value"] for r in search_link(doctype, "", filters={"project": self.ALP})}
			self.assertIn(mine, found)
			self.assertNotIn(other, found)

	def test_a_project_filter_narrows_every_block(self):
		data = self.data(project=self.ALP)
		self.assertEqual(self.names(data["projects"]), {self.ALP})
		self.assertEqual(data["kpis"]["projects"], 1)
		self.assertEqual(data["kpis"]["tasks_total"], self.row_total(self.ALP))
		self.assertTrue({r["project"] for r in data["releases"]} <= {self.ALP})
		self.assertTrue({s["project"] for s in data["sprints"]} <= {self.ALP})
		self.assertNotIn(self.bet_rel, self.names(data["releases"]))

	def row_total(self, project):
		return frappe.db.count("Work Item", {"project": project})

	def test_a_release_filter_keeps_that_release_its_tickets_and_its_sprints(self):
		data = self.data(project=self.ALP, release=self.alp_rel)
		self.assertEqual(self.names(data["releases"]), {self.alp_rel})
		self.assertEqual(data["kpis"]["tasks_total"], 2)
		self.assertEqual(data["kpis"]["tasks_overdue"], 1)
		self.assertEqual(self.names(data["sprints"]), {self.alp_sprint})
		people = {u["user"]: u for u in data["users"]}
		self.assertEqual((people[DEV]["pending"], people[MGR]["pending"]), (1, 1))

	def test_a_release_without_a_sprint_leaves_the_sprint_block_empty(self):
		data = self.data(project=self.ALP, release=self.alp_rel2)
		self.assertEqual(data["sprints"], [])
		self.assertEqual(data["kpis"]["tasks_total"], 1)

	def test_a_sprint_filter_keeps_that_sprint_and_the_releases_of_its_tickets(self):
		data = self.data(project=self.ALP, sprint=self.alp_sprint)
		self.assertEqual(self.names(data["sprints"]), {self.alp_sprint})
		self.assertEqual(self.names(data["releases"]), {self.alp_rel})
		self.assertEqual(data["kpis"]["tasks_total"], 2)

	def test_release_and_sprint_together_are_an_intersection(self):
		data = self.data(project=self.ALP, release=self.alp_rel, sprint=self.alp_sprint)
		self.assertEqual(data["kpis"]["tasks_total"], 2)
		data = self.data(project=self.ALP, release=self.alp_rel2, sprint=self.alp_sprint)
		self.assertEqual(data["kpis"]["tasks_total"], 0)

	def test_the_filters_are_echoed_so_the_page_can_show_them(self):
		data = self.data(project=self.ALP, release=self.alp_rel)
		self.assertEqual(
			data["filters"], {"projects": [self.ALP], "project": self.ALP, "release": self.alp_rel, "sprint": ""}
		)

	def test_several_projects_can_be_chosen(self):
		"""A list, comma-separated names or a JSON list narrow the page to exactly those projects."""
		import json

		both = f"{self.ALP},{self.BET}"
		for value in ([self.ALP, self.BET], both, json.dumps([self.ALP, self.BET])):
			data = self.data(project=value)
			self.assertEqual({p["name"] for p in data["projects"]} & {self.ALP, self.BET}, {self.ALP, self.BET})
			self.assertEqual(data["filters"]["projects"], [self.ALP, self.BET])
			self.assertEqual(data["filters"]["project"], "")  # more than one: no single project
		one = self.data(project=[self.ALP, self.ALP])  # a repeated name counts once
		self.assertEqual(one["filters"]["projects"], [self.ALP])

	def test_the_totals_cover_only_the_chosen_projects(self):
		self.new_item(MGR, tracker="Task", project=self.ALP)
		self.new_item(MGR, tracker="Task", project=self.BET)
		alp, bet = self.data(project=self.ALP), self.data(project=self.BET)
		both = self.data(project=[self.ALP, self.BET])
		self.assertEqual(both["kpis"]["projects"], 2)
		self.assertEqual(both["kpis"]["tasks_total"], alp["kpis"]["tasks_total"] + bet["kpis"]["tasks_total"])
		self.assertEqual({r["project"] for r in both["releases"]}, {r["project"] for r in alp["releases"] + bet["releases"]})
		hours = {r["name"] for r in both["hours"]["projects"]}
		self.assertEqual(hours, {self.ALP, self.BET})

	def test_releases_and_sprints_are_offered_only_for_the_chosen_projects(self):
		options = self.data(project=[self.ALP, self.BET])["options"]
		self.assertTrue({self.alp_rel, self.bet_rel} <= self.names(options["releases"]))
		only_alp = self.data(project=[self.ALP])["options"]
		self.assertNotIn(self.bet_rel, self.names(only_alp["releases"]))
		self.assertTrue({self.ALP, self.BET} <= self.names(only_alp["projects"]))  # the project list never shrinks

	def test_a_release_must_belong_to_one_of_the_chosen_projects(self):
		self.data(project=[self.ALP, self.BET], release=self.bet_rel)  # fine: Beta is chosen
		with self.as_user(TM), self.assertRaises(frappe.ValidationError):
			api.get_management_dashboard(project=[self.ALP], release=self.bet_rel)

	def test_a_bad_project_in_the_list_refuses_the_whole_request(self):
		with self.as_user(MGR), self.assertRaises(frappe.PermissionError):
			api.get_management_dashboard(project=[self.ALP, self.GAM])  # Gamma is not one of MGR's projects
		with self.as_user(TM), self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
			api.get_management_dashboard(project=[self.ALP, self.GAM])  # an admin too: Auri PMS is off there

	def test_a_release_or_sprint_of_another_project_is_refused(self):
		self.assertRaises(frappe.ValidationError, self.data, project=self.ALP, release=self.bet_rel)
		self.assertRaises(frappe.ValidationError, self.data, project=self.ALP, sprint=self.bet_sprint)
		self.assertRaises(frappe.ValidationError, self.data, release="no-such-release")

	def test_a_project_outside_the_audience_is_refused(self):
		self.assertRaises(frappe.PermissionError, self.data, project=self.GAM)  # Auri PMS is off there
		self.assertRaises(frappe.PermissionError, self.data, DEV, project=self.ALP)  # a Developer has no dashboard

	def test_a_manager_is_offered_only_the_releases_of_the_projects_they_manage(self):
		bet = frappe.get_doc("Project", self.BET)
		for row in list(bet.tracker_members):
			if row.user == MGR:
				bet.remove(row)
		bet.append("tracker_members", {"user": DEV, "project_role": "Manager"})
		bet.save(ignore_permissions=True)
		options = self.data(MGR)["options"]
		self.assertIn(self.alp_rel, self.names(options["releases"]))
		self.assertNotIn(self.bet_rel, self.names(options["releases"]))
		self.assertRaises(frappe.PermissionError, self.data, MGR, project=self.BET)

	def test_the_sprint_burndown_report_checks_the_project(self):
		from auri_pms.auri_pms.report.sprint_burndown.sprint_burndown import execute

		with self.as_user(MGR):
			execute({"project": self.ALP, "sprint": self.alp_sprint})
			self.assertRaises(frappe.ValidationError, execute, {"project": self.BET, "sprint": self.alp_sprint})

	def test_a_work_item_cannot_take_a_release_or_sprint_of_another_project(self):
		item = self.new_item(MGR, subject="Alpha ticket")
		self.assertThrows("does not belong to Project", lambda: self.save_as(MGR, item, release=self.bet_rel))
		item = self.new_item(MGR, subject="Alpha ticket 2")
		self.assertThrows("does not belong to Project", lambda: self.save_as(MGR, item, sprint=self.bet_sprint))
