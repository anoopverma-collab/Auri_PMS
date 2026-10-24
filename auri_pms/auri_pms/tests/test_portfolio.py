"""Portfolio dashboard (projects the user manages; every project for Auri PMS Managers)."""

import frappe
from frappe.utils import add_days, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.dashboards import average_score
from auri_pms.auri_pms.tests.utils import BOSS, DEV, MGR, OUT, TM, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestPortfolio(TrackerTestCase):
	def portfolio(self, user=TM, period="3m"):
		with self.as_user(user):
			data = api.get_portfolio(period)
		return data, {p.name: p for p in data.projects}

	def test_visibility(self):
		"""Auri PMS Managers see every project; a project's own manager only the projects they manage."""
		_data, tm = self.portfolio(TM)
		self.assertTrue({self.ALP, self.BET} <= set(tm))
		self.assertNotIn(self.GAM, tm)  # no identifier: not part of the portfolio
		_data, mgr = self.portfolio(MGR)  # Manager on Alpha and Beta
		self.assertEqual(set(mgr), {self.ALP, self.BET})

	def test_members_without_a_managing_role_have_no_portfolio(self):
		"""A Developer (or anyone outside the projects) is refused, even on a public project."""
		for user in (DEV, OUT):
			with self.as_user(user), self.assertRaises(frappe.PermissionError):
				api.get_portfolio("3m")

	def test_a_project_manager_sees_only_the_projects_they_manage(self):
		"""Developer on Alpha but Manager on Beta: the Portfolio shows Beta only."""
		bet = frappe.get_doc("Project", self.BET)
		bet.append("tracker_members", {"user": DEV, "project_role": "Manager"})
		bet.save(ignore_permissions=True)
		_data, dev = self.portfolio(DEV)
		self.assertEqual(set(dev), {self.BET})

	def test_row_numbers(self):
		"""Open, overdue, completion, hours and billable share per project."""
		first = self.new_item(MGR, tracker="Task", estimated_hours=10, due_date=days(-2))
		self.new_item(MGR, tracker="Task", estimated_hours=10)
		done = self.new_item(MGR, tracker="Task", estimated_hours=10)
		self.save_as(MGR, done, status="Closed")
		self.logged_time(DEV, first.name, 6)
		self.logged_time(DEV, first.name, 2, is_billable=0, activity="Meeting")
		_data, rows = self.portfolio()
		row = rows[self.ALP]
		self.assertEqual((row.open, row.closed, row.total, row.overdue), (2, 1, 3, 1))
		self.assertEqual((row.hours_spent, row.billable_pct, row.estimated), (8, 75, 30))
		self.assertEqual(row.burn_pct, 26.7)
		self.assertEqual(row.identifier, "ALP")

	def test_status_and_sorting(self):
		"""Projects are sorted red first; the headline is the first risk."""
		self.new_item(MGR, tracker="Task", due_date=days(-3))
		self.new_item(MGR, tracker="Task", due_date=days(-1))
		data, rows = self.portfolio()
		self.assertEqual(rows[self.ALP].level, "red")
		self.assertIn("overdue", rows[self.ALP].headline)
		levels = [p.level for p in data.projects]
		self.assertEqual(levels, sorted(levels, key=["red", "amber", "green", "none"].index))
		scores = [p.score for p in data.projects if p.level == "red"]
		self.assertEqual(scores, sorted(scores))  # within a level the weakest project comes first

	def test_totals_and_series(self):
		"""Portfolio totals add up the projects and the series share one set of labels."""
		self.new_item(MGR, tracker="Task")
		self.new_item(MGR, self.BET, tracker="Task")
		data, rows = self.portfolio()
		self.assertEqual(data.kpis.projects, len(rows))
		self.assertEqual(data.kpis.open, sum(r.open for r in rows.values()))
		self.assertEqual(
			data.kpis.red + data.kpis.amber + data.kpis.green + data.kpis.none + data.kpis.hidden, len(rows)
		)
		for series in data.series.values():
			self.assertEqual(len(series), len(data.labels))
		self.assertEqual(sum(data.series.created), sum(r.created_period for r in rows.values()))

	def test_active_sprint_on_the_row(self):
		"""The active sprint and its progress appear on the project row."""
		with self.as_user(MGR):
			sprint = frappe.get_doc(
				{
					"doctype": "Sprint",
					"sprint_name": "S1",
					"project": self.ALP,
					"start_date": days(-2),
					"end_date": days(11),
					"status": "Active",
				}
			).insert()
		item = self.new_item(MGR, tracker="Task", sprint=sprint.name)
		self.save_as(MGR, item, status="Closed")
		_data, rows = self.portfolio()
		self.assertEqual((rows[self.ALP].sprint.name, rows[self.ALP].sprint.percent), (sprint.name, 100))

	def test_periods(self):
		"""Every period works and keeps the series aligned."""
		self.new_item(MGR, tracker="Task")
		for period, size in (("1m", 5), ("3m", 13), ("6m", 26)):
			data, _rows = self.portfolio(TM, period)
			self.assertEqual(len(data.labels), size)
		data, _rows = self.portfolio(TM, "all")
		self.assertEqual(len(data.series.created), len(data.labels))

	def test_average_score_rounds_half_up(self):
		"""Two projects at 45 and 100 average 72.5, shown as 73; projects without a score are ignored."""
		self.assertEqual(average_score([45, 100]), 73)
		self.assertEqual(average_score([45, None, 100]), 73)
		self.assertEqual(average_score([80, 81]), 81)
		self.assertEqual(average_score([None]), 0)
		self.assertEqual(average_score([]), 0)

	def test_every_project_row_has_a_trend_for_each_period(self):
		"""The trend lines need one number per week (or month) for every project and metric."""
		data, rows = self.portfolio(TM)
		for project in rows.values():
			self.assertEqual(
				set(project.trend), {"open", "created", "resolved", "hours", "billable", "non_billable"}
			)
			for values in project.trend.values():
				self.assertEqual(len(values), len(data.labels))

	def test_billing_summary_counts_tickets_hours_and_categories(self):
		"""Billable ticket = billable hours logged on it; hours are grouped by the ticket's category."""
		cat = frappe.get_doc(
			{"doctype": "Work Item Category", "category_name": "Billing QA", "project": self.ALP}
		).insert(ignore_permissions=True)
		billable = self.new_item(MGR, tracker="Task", category=cat.name)
		internal = self.new_item(MGR, tracker="Task", category=cat.name)
		self.new_item(MGR, tracker="Task")  # nothing logged
		self.logged_time(MGR, billable.name, 3, project=self.ALP, is_billable=1)
		self.logged_time(MGR, internal.name, 2, project=self.ALP, is_billable=0)
		self.logged_time(MGR, None, 1, project=self.ALP, is_billable=0)  # no ticket
		_data, rows = self.portfolio(TM)
		billing = rows[self.ALP].billing
		self.assertEqual(billing.tickets, {"billable": 1, "non_billable": 1, "no_time": 1})
		self.assertEqual(
			(billing.names["billable"], billing.names["non_billable"], len(billing.names["no_time"])),
			([billable.name], [internal.name], 1),
		)
		self.assertFalse(billing.names_capped)
		self.assertEqual(billing.hours, {"billable": 3, "non_billable": 3})
		by_label = {c["label"]: c for c in billing.categories}
		self.assertEqual((by_label["Billing QA"]["billable"], by_label["Billing QA"]["non_billable"]), (3, 2))
		self.assertEqual(by_label["No ticket"]["non_billable"], 1)
		self.assertEqual(
			by_label["Billing QA"]["docnames"], [cat.name]
		)  # the category record, so its tickets can be opened
		total = sum(c["billable"] + c["non_billable"] for c in billing.categories)
		self.assertEqual(total, 6)

	def test_ticket_table_counts_created_closed_and_in_progress_for_a_period(self):
		"""Overall by default; a period counts what was created or closed inside it."""
		started = self.new_item(MGR, tracker="Task")
		self.save_as(MGR, started, status="In Progress")
		done = self.new_item(MGR, tracker="Task")
		self.save_as(MGR, done, status="Closed")
		idle = self.new_item(MGR, tracker="Task")
		self.new_item(MGR, tracker="Task", dependent_on_client=1, client_dependency_note="needs the data")
		self.logged_time(MGR, started.name, 3, project=self.ALP, is_billable=1)
		self.logged_time(MGR, idle.name, 2, project=self.ALP, is_billable=0)

		def row(**dates):
			with self.as_user(TM):
				return next(r for r in api.get_portfolio_tickets(**dates) if r["project"] == self.ALP)

		overall = row()
		self.assertEqual((overall["created"], overall["closed"], overall["in_progress"]), (4, 1, 1))
		self.assertEqual(overall["client_dependent"], 1)
		self.assertEqual(
			(overall["billable_hours"], overall["spent_hours"]), (3, 5)
		)  # billable time against the actual hours spent
		today_ = today()
		this_period = row(from_date=today_, to_date=today_)
		self.assertEqual(
			(this_period["created"], this_period["closed"], this_period["in_progress"]), (4, 1, 1)
		)
		self.assertEqual(this_period["client_dependent"], 1)
		past = row(from_date=add_days(today_, -30), to_date=add_days(today_, -1))
		self.assertEqual((past["created"], past["closed"], past["in_progress"]), (0, 0, 0))
		self.assertEqual((past["billable_hours"], past["spent_hours"], past["client_dependent"]), (0, 0, 0))
		swapped = row(from_date=today_, to_date=add_days(today_, -30))
		self.assertEqual(swapped["created"], 4)  # the dates are put in order: the last 30 days up to today

	def test_ticket_table_follows_the_portfolio_access_rules(self):
		with self.as_user(DEV), self.assertRaises(frappe.PermissionError):
			api.get_portfolio_tickets()
		with self.as_user(MGR):
			projects = {r["project"] for r in api.get_portfolio_tickets()}
		self.assertEqual(projects, {self.ALP, self.BET})

	def test_project_health_carries_billing_notes_and_period_counts(self):
		"""Health gets the Portfolio's billing, notes and period table for its one project."""
		item = self.new_item(MGR, tracker="Task")
		self.logged_time(MGR, item.name, 3, project=self.ALP, is_billable=1)
		with self.as_user(MGR):
			api.add_project_note(self.ALP, "Health note")
			data = api.get_project_health(self.ALP)
			periods = api.get_project_periods(
				self.ALP,
				[
					{"key": "all"},
					{"key": "today", "from_date": today(), "to_date": today()},
					{"key": "past", "from_date": add_days(today(), -9), "to_date": add_days(today(), -5)},
				],
			)
		self.assertEqual(data.billing["hours"]["billable"], 3)
		self.assertEqual(data.billing["tickets"]["billable"], 1)
		self.assertEqual(data.notes["count"], 1)
		self.assertTrue(all(self.ALP in m["member_of"] for m in data.team["people"]))
		self.assertEqual(data.team["burnout"], sum(m["burnout"] for m in data.team["people"]))
		self.assertTrue(data.can_note)
		self.assertEqual(len(data.starts), len(data.labels))
		by = {r["key"]: r for r in periods}
		self.assertEqual((by["all"]["created"], by["all"]["billable_hours"]), (1, 3))
		self.assertEqual(by["today"]["spent_hours"], 3)
		self.assertEqual((by["past"]["created"], by["past"]["spent_hours"]), (0, 0))
		with self.as_user(OUT), self.assertRaises(frappe.PermissionError):
			api.get_project_periods(self.ALP, [{"key": "all"}])

	def test_portfolio_data_carries_the_start_of_every_period(self):
		data, _rows = self.portfolio(TM)
		self.assertEqual(len(data.starts), len(data.labels))

	def test_project_notes_are_added_listed_and_shown_on_the_row(self):
		"""A project's manager adds a note; it is listed newest first, counted on the Portfolio row and kept on the Project."""
		with self.as_user(MGR):
			api.add_project_note(self.ALP, "First note")
			notes = api.add_project_note(self.ALP, "Second note\nwith two lines")
			self.assertEqual(notes[0]["text"], "Second note\nwith two lines")
			self.assertEqual(len(notes), 2)
			self.assertEqual(notes[0]["by"], MGR)
			self.assertEqual(len(api.get_project_notes(self.ALP)), 2)
			row = next(p for p in api.get_portfolio("3m").projects if p.name == self.ALP)
		self.assertEqual(row.notes["count"], 2)
		self.assertIn("Second note", row.notes["last"]["text"])
		self.assertTrue(
			frappe.db.exists("Comment", {"reference_doctype": "Project", "reference_name": self.ALP})
		)

	def test_project_notes_follow_the_portfolio_access_rules(self):
		with self.as_user(DEV):
			self.assertRaises(frappe.PermissionError, api.add_project_note, self.ALP, "no")
			self.assertRaises(frappe.PermissionError, api.get_project_notes, self.ALP)
		with self.as_user(MGR):
			self.assertRaises(frappe.ValidationError, api.add_project_note, self.ALP, "   ")
			self.assertRaises(frappe.ValidationError, api.add_project_note, self.ALP, "x" * 2001)

	def test_a_note_can_be_deleted_by_its_author_or_an_admin_only(self):
		with self.as_user(MGR):
			notes = api.add_project_note(self.ALP, "mine")
			self.assertTrue(notes[0]["can_delete"])
			api.add_project_note(self.ALP, "second")
			own = api.get_project_notes(self.ALP)
		with self.as_user(TM):  # an admin sees every note as deletable
			self.assertTrue(all(n["can_delete"] for n in api.get_project_notes(self.ALP)))
		# another manager of the project cannot delete a note that is not theirs
		self.join(self.ALP, BOSS, "Manager")
		with self.as_user(BOSS):
			self.assertFalse(any(n["can_delete"] for n in api.get_project_notes(self.ALP)))
			self.assertRaises(frappe.PermissionError, api.delete_project_note, self.ALP, own[0]["name"])
		with self.as_user(MGR):
			left = api.delete_project_note(self.ALP, own[0]["name"])
			self.assertEqual(len(left), 1)
			self.assertRaises(
				frappe.ValidationError, api.delete_project_note, self.ALP, own[0]["name"]
			)  # already gone
			self.assertRaises(
				frappe.ValidationError, api.delete_project_note, self.BET, left[0]["name"]
			)  # not a note of that project
		with self.as_user(TM):
			self.assertEqual(api.delete_project_note(self.ALP, left[0]["name"]), [])

	def join(self, project, user, role):
		doc = frappe.get_doc("Project", project)
		doc.append("tracker_members", {"user": user, "project_role": role})
		doc.save(ignore_permissions=True)
