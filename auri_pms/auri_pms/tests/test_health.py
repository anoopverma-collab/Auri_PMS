"""Project Health calculations (flow, billable time, status rules, velocity)."""

import frappe
from frappe.utils import add_days, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.health import get_health, make_buckets, monday
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestProjectHealth(TrackerTestCase):
	def aged_item(self, created=0, closed=None, **kw):
		"""Create an item and back-date its creation (and closing) like a project with history."""
		item = self.new_item(MGR, tracker=kw.pop("tracker", "Task"), **kw)
		if closed is not None:
			self.save_as(MGR, item, status="Closed")
			frappe.db.set_value(
				"Work Item", item.name, "closed_on", f"{days(closed)} 15:00:00", update_modified=False
			)
		frappe.db.set_value(  # back-date last: Frappe forbids changing "creation" on a loaded document
			"Work Item", item.name, "creation", f"{days(created)} 09:00:00", update_modified=False
		)
		item.reload()
		return item

	def health(self, period="3m"):
		return get_health(self.ALP, period)

	def test_open_closed_and_completion(self):
		"""Open vs closed counts, completion % and estimated hours of open/closed work."""
		self.aged_item(-2, estimated_hours=4)
		self.aged_item(-1, estimated_hours=6)
		self.aged_item(-5, closed=-1, estimated_hours=10)
		flow = self.health().flow
		self.assertEqual((flow.total, flow.open, flow.closed, flow.completion_pct), (3, 2, 1, 33.3))
		self.assertEqual((flow.estimated_open_hours, flow.estimated_closed_hours), (10, 10))

	def test_created_vs_resolved_per_week(self):
		"""Weekly created/resolved series end with the current week; resolved counts closing dates."""
		self.aged_item(-20, closed=-10)  # created three weeks ago, resolved ~1.5 weeks ago
		self.aged_item(-1)
		self.aged_item(0)
		health = self.health()
		self.assertEqual(len(health.labels), 13)
		self.assertEqual(
			health.flow.created[-1] + health.flow.created[-2], 2
		)  # last two weeks (today and yesterday)
		self.assertEqual(health.flow.created[-3] + health.flow.created[-4] + health.flow.created[-5], 1)
		self.assertEqual(sum(health.flow.resolved), 1)
		self.assertEqual((health.flow.created_total, health.flow.resolved_total), (3, 1))

	def test_open_backlog_trend(self):
		"""The open-backlog line grows with creations and drops when work is resolved."""
		self.aged_item(-20, closed=-10)
		self.aged_item(-18)
		self.aged_item(0)
		trend = self.health().flow.open_trend
		self.assertEqual(trend[-1], 2)  # one resolved, two still open today
		self.assertGreaterEqual(max(trend), 2)

	def test_aging_and_resolution_time(self):
		"""Open tickets land in age buckets; resolution time averages creation to closing."""
		self.aged_item(-3)
		self.aged_item(-12)
		self.aged_item(-40)
		self.aged_item(-100)
		self.aged_item(-10, closed=-4)
		self.aged_item(-20, closed=-10)
		flow = self.health().flow
		self.assertEqual(
			{a["label"]: a["count"] for a in flow.aging},
			{"0-7d": 1, "8-14d": 1, "15-30d": 0, "31-60d": 1, "60d+": 1},
		)
		self.assertEqual(flow.avg_resolution_days, 8.0)  # (6 + 10) / 2

	def test_billable_vs_non_billable_time(self):
		"""Hours split into billable and non-billable, in total, per week, person and activity."""
		item = self.aged_item(-2, estimated_hours=20)
		self.logged_time(DEV, item.name, 6, date=days(-1))
		self.logged_time(DEV, item.name, 2, date=days(-1), is_billable=0, activity="Meeting")
		self.logged_time(MGR, item.name, 4, date=days(-9))
		time = self.health().time
		self.assertEqual((time.spent, time.billable, time.non_billable, time.billable_pct), (12, 10, 2, 83.3))
		self.assertEqual((time.estimated, time.burn_pct), (20, 60.0))
		self.assertEqual(sum(time.billable_by_week), 10)
		self.assertEqual(sum(time.non_billable_by_week), 2)
		by_user = {u["user"]: (u["billable"], u["non_billable"]) for u in time.by_user}
		self.assertEqual(by_user, {DEV: (6, 2), MGR: (4, 0)})
		self.assertEqual({a["label"]: a["non_billable"] for a in time.by_activity}["Meeting"], 2)

	def test_time_entries_are_billable_by_default(self):
		"""A new Time Entry is billable unless marked otherwise; log_time can set it."""
		item = self.aged_item(-1)
		self.assertEqual(self.logged_time(DEV, item.name, 1).is_billable, 1)
		with self.as_user(DEV):
			name = api.log_time(item.name, 1, "Meeting", comment="Sync", is_billable=0)
		self.assertEqual(frappe.db.get_value("Time Entry", name, "is_billable"), 0)

	def test_status_green_when_clean(self):
		"""No overdue, no effort or release risk: On Track."""
		self.aged_item(-2, estimated_hours=10)
		status = self.health().status
		self.assertEqual((status.level, status.label, status.score), ("green", "On Track", 100))

	def test_status_red_on_overdue_and_budget(self):
		"""Many overdue tickets and spending over the estimate make the project Off Track with reasons."""
		first = self.aged_item(-10, estimated_hours=2, due_date=days(-3))
		self.aged_item(-10, estimated_hours=2, due_date=days(-2))
		self.logged_time(DEV, first.name, 5)
		status = self.health().status
		texts = " | ".join(r["text"] for r in status.reasons)
		self.assertEqual(status.level, "red")
		self.assertIn("overdue", texts)
		self.assertIn("exceed the estimate", texts)
		self.assertLessEqual(status.score, 50)

	def test_status_amber_for_effort_ahead_of_progress(self):
		"""Effort used far ahead of completed work is flagged At Risk."""
		first = self.aged_item(-5, estimated_hours=10)
		self.aged_item(-5, estimated_hours=10)
		self.logged_time(DEV, first.name, 8)  # 40% burned, 0% done
		status = self.health().status
		self.assertEqual(status.level, "amber")
		self.assertIn("ahead of work completed", status.reasons[0]["text"])

	def test_release_risk_feeds_status(self):
		"""A release past its due date with open work turns the project red."""
		release = self.world.releases["v1"]
		frappe.db.set_value("Release", release, "due_date", days(-2))
		self.aged_item(-3, release=release)
		releases = {r["name"]: r for r in self.health().releases}
		self.assertEqual(releases[release]["risk"], "late")
		self.assertEqual(self.health().status.level, "red")

	def test_status_carries_the_working_of_its_score(self):
		from auri_pms.auri_pms.health import status_from_reasons

		status = status_from_reasons(
			[{"level": "red", "text": "a"}, {"level": "amber", "text": "b"}, {"level": "amber", "text": "c"}]
		)
		self.assertEqual(status["calc"], {"red": 1, "amber": 2, "red_penalty": 25, "amber_penalty": 10})
		self.assertEqual(status["score"], 100 - 25 - 2 * 10)
		# below zero the score stops at 0
		many = status_from_reasons([{"level": "red", "text": str(i)} for i in range(6)])
		self.assertEqual((many["score"], many["calc"]["red"]), (0, 6))

	def test_velocity_of_completed_sprints(self):
		"""Completed sprints report the tickets and hours they delivered."""
		with self.as_user(MGR):
			sprint = frappe.get_doc(
				{
					"doctype": "Sprint",
					"sprint_name": "S1",
					"project": self.ALP,
					"start_date": days(-14),
					"end_date": days(-1),
					"status": "Active",
				}
			).insert()
		item = self.new_item(MGR, tracker="Task", sprint=sprint.name, estimated_hours=6)
		self.save_as(MGR, item, status="Closed")
		self.save_as(MGR, sprint, status="Completed")
		self.assertEqual(
			self.health().velocity, [{"name": sprint.name, "sprint": "S1", "items": 1, "hours": 6.0}]
		)

	def test_empty_project_has_no_status(self):
		"""A project without tickets shows 'No data yet'."""
		self.assertEqual(self.health().status.level, "none")

	def test_access_rules(self):
		"""Members can load the health data; outsiders cannot open a private project."""
		self.aged_item(-1)
		with self.as_user(DEV):
			self.assertEqual(api.get_project_health(self.ALP)["flow"]["total"], 1)
		with self.as_user(OUT):
			self.assertRaises(frappe.PermissionError, api.get_project_health, self.ALP)

	def test_weeks_start_on_monday(self):
		"""Week buckets start on Monday."""
		self.assertEqual(monday(frappe.utils.getdate("2026-10-10")).weekday(), 0)

	def test_period_options(self):
		"""1 month, 3 months and 6 months use 5, 13 and 26 weekly buckets; unknown values fall back to 3 months."""
		self.aged_item(-3)
		sizes = {p: len(self.health(p).labels) for p in ("1m", "3m", "6m")}
		self.assertEqual(sizes, {"1m": 5, "3m": 13, "6m": 26})
		self.assertEqual(len(self.health("nonsense").labels), 13)
		self.assertEqual(self.health("1m").bucket, "week")

	def test_overall_starts_at_the_first_activity(self):
		"""Overall covers the whole project: weekly while it is young, monthly once it is older than 26 weeks."""
		self.aged_item(-60)  # about 9 weeks old
		overall = self.health("all")
		first = frappe.utils.getdate(days(-60))
		expected = (monday(frappe.utils.getdate(today())) - monday(first)).days // 7 + 1
		self.assertEqual((overall.bucket, len(overall.labels)), ("week", expected))
		self.assertEqual(sum(overall.flow.created), 1)  # nothing is cut off
		self.aged_item(-400)
		overall = self.health("all")
		self.assertEqual(overall.bucket, "month")
		self.assertEqual(sum(overall.flow.created), 2)
		self.assertTrue(overall.labels[0].endswith(str(frappe.utils.getdate(days(-400)).year)[2:]))

	def test_period_only_changes_the_charts_not_the_totals(self):
		"""Open/closed totals describe the whole project whatever the range; charted activity follows the range."""
		self.aged_item(-100, closed=-90)
		self.aged_item(-2)
		one, overall = self.health("1m"), self.health("all")
		self.assertEqual((one.flow.total, one.flow.closed), (overall.flow.total, overall.flow.closed))
		self.assertEqual(sum(one.flow.created), 1)  # only the recent ticket falls in the last month
		self.assertEqual(sum(overall.flow.created), 2)

	def test_month_buckets(self):
		"""Month buckets start on the 1st and end on the last day (capped at today)."""
		buckets = make_buckets("all", frappe.utils.getdate("2025-01-15"), frappe.utils.getdate("2026-10-10"))
		self.assertEqual(buckets.kind, "month")
		self.assertEqual(buckets.starts[0], frappe.utils.getdate("2025-01-01"))
		self.assertEqual(str(buckets.end(frappe.utils.getdate("2026-02-01"))), "2026-02-28")
		self.assertEqual(str(buckets.end(frappe.utils.getdate("2026-10-01"))), "2026-10-10")
