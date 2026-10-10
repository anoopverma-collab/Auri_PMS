"""Tickets that depend on the client: the checkbox, its counts and where they show up."""

import frappe
from frappe.desk.query_report import run as run_report
from frappe.utils import add_days, today

from auri_pms.tracking import api
from auri_pms.tracking.dashboards import get_my_work_data
from auri_pms.tracking.health import get_health
from auri_pms.tracking.status_report import build_report, render_html
from auri_pms.tracking.tests.utils import DEV, MGR, TM, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestClientDependency(TrackerTestCase):
	def waiting(self, since=0, note="Please send the logo files", **kw):
		"""A ticket that depends on the client, optionally back-dated."""
		tracker = kw.pop("tracker", "Task")
		item = self.new_item(MGR, tracker=tracker, dependent_on_client=1, client_dependency_note=note, **kw)
		if since:
			frappe.db.set_value(
				"Work Item", item.name, "client_dependency_since", days(-since), update_modified=False
			)
		item.reload()
		return item

	def test_ticking_stamps_the_date_and_unticking_clears_it(self):
		"""'Waiting since' is set automatically; unticking clears it and the note."""
		item = self.waiting()
		self.assertEqual(
			(str(item.client_dependency_since), item.client_dependency_note),
			(today(), "Please send the logo files"),
		)
		self.save_as(MGR, item, subject="Edited")  # unrelated edits keep the original date
		self.assertEqual(str(item.client_dependency_since), today())
		self.save_as(MGR, item, dependent_on_client=0)
		self.assertEqual((item.client_dependency_since, item.client_dependency_note), (None, None))

	def test_date_is_kept_across_saves_and_restamped_when_ticked_again(self):
		"""The waiting date survives saves; ticking again after a break starts a new wait."""
		item = self.waiting(since=5)
		self.save_as(MGR, item, priority="High")
		self.assertEqual(str(item.client_dependency_since), days(-5))
		self.save_as(MGR, item, dependent_on_client=0)
		self.save_as(MGR, item, dependent_on_client=1)
		self.assertEqual(str(item.client_dependency_since), today())

	def test_hub_counts_open_tickets_only(self):
		"""The hub counts open client-dependent tickets and the oldest wait; closed ones drop out."""
		self.waiting(since=9)
		closed = self.waiting(since=3)
		self.save_as(MGR, closed, status="Closed")
		self.new_item(MGR, tracker="Task")
		with self.as_user(DEV):
			numbers = api.get_project_hub(self.ALP)["numbers"]
		self.assertEqual((numbers["client_dependent"], numbers["client_oldest_days"]), (1, 9))

	def test_health_numbers_and_info_reason(self):
		"""Health reports the count, oldest/average wait and an informational reason that does not change the status."""
		self.waiting(since=10)
		self.waiting(since=4)
		health = get_health(self.ALP, "3m")
		self.assertEqual(
			(health.flow.client_dependent, health.flow.client_oldest_days, health.flow.client_avg_days),
			(2, 10, 7.0),
		)
		info = [r for r in health.status.reasons if r["level"] == "info"]
		self.assertEqual(len(info), 1)
		self.assertIn("2 tickets are waiting on the client (oldest 10 days)", info[0]["text"])
		self.assertEqual((health.status.level, health.status.score), ("green", 100))

	def test_overdue_waiting_on_client_is_not_a_delivery_delay(self):
		"""Overdue tickets that wait on the client do not turn the status red; the same tickets without the flag do."""
		first, second = self.waiting(due_date=days(-5)), self.waiting(due_date=days(-4))
		health = get_health(self.ALP, "3m")
		self.assertEqual(
			(health.flow.overdue, health.flow.overdue_client, health.flow.overdue_delivery), (2, 2, 0)
		)
		self.assertEqual(health.status.level, "green")
		for item in (first, second):
			self.save_as(MGR, item, dependent_on_client=0)
		self.assertEqual(get_health(self.ALP, "3m").status.level, "red")

	def test_portfolio_counts(self):
		"""The portfolio row and total count tickets waiting on the client."""
		self.waiting()
		self.waiting()
		with self.as_user(TM):
			data = api.get_portfolio("3m")
		rows = {p.name: p for p in data.projects}
		self.assertEqual(rows[self.ALP].client_dependent, 2)
		self.assertGreaterEqual(data.kpis.client_dependent, 2)

	def test_my_work_flags_my_waiting_tickets(self):
		"""My Work counts and marks my tickets that wait on the client."""
		item = self.waiting(assigned_to=DEV)
		self.new_item(MGR, tracker="Task", assigned_to=DEV)
		data = get_my_work_data(DEV)
		self.assertEqual(data.tiles.client_waiting, 1)
		rows = [r for group in data.groups.values() for r in group]
		flagged = {r.name: r.dependent_on_client for r in rows}
		self.assertEqual(flagged[item.name], 1)
		self.assertEqual(sum(flagged.values()), 1)

	def test_status_report_has_a_waiting_on_you_section(self):
		"""The client report lists what we need, how long it has been waiting, and keeps those tickets out of 'overdue'."""
		item = self.waiting(since=6, due_date=days(-3), subject="Logo files")
		report = build_report(self.ALP, days(-7), days(0))
		self.assertEqual(report.summary.waiting, 1)
		self.assertEqual([(w["name"], w["days"]) for w in report.waiting], [(item.name, 6)])
		self.assertEqual(report.overdue, [])
		html = render_html(report)
		self.assertIn("Waiting on you", html)
		self.assertIn("Please send the logo files", html)
		self.assertIn("6 days", html)

	def test_work_item_summary_report_column(self):
		"""Work Item Summary shows how many open tickets wait on the client per project."""
		self.waiting()
		self.waiting()
		self.new_item(MGR, tracker="Task")
		with self.as_user(TM):
			result = run_report("Work Item Summary", {"project": self.ALP})["result"]
		self.assertEqual(result[0]["client_waiting"], 2)

	def test_filter_finds_the_tickets(self):
		"""The standard filter lists exactly the client-dependent tickets."""
		item = self.waiting()
		self.new_item(MGR, tracker="Task")
		with self.as_user(MGR):
			names = frappe.get_list(
				"Work Item", filters={"dependent_on_client": 1, "project": self.ALP}, pluck="name"
			)
		self.assertEqual(names, [item.name])

	def test_hub_lists_the_waiting_tickets_longest_first(self):
		"""The hub returns the waiting tickets with what we need and how long they have waited."""
		self.waiting(since=3, note="Newer request", subject="Newer")
		old = self.waiting(since=11, note="Older request", subject="Older")
		with self.as_user(DEV):
			data = api.get_project_hub(self.ALP)
		first = data["client_tickets"][0]
		self.assertEqual(first["name"], old.name)
		self.assertEqual((first["days"], first["note"], first["subject"]), (11, "Older request", "Older"))
		self.assertEqual(data["backlog_client"], 2)

	def test_open_breakdowns_split_out_the_client_part(self):
		"""Open by status, type, priority and age all say how many of the open tickets wait on the client."""
		self.waiting(priority="High")
		plain = self.new_item(MGR, tracker="Task", priority="High")
		self.save_as(MGR, plain, status="In Progress")
		flow = get_health(self.ALP, "3m").flow
		by_status = {r.label: (r.count, r.client) for r in flow.open_by_status}
		self.assertEqual(by_status, {"New": (1, 1), "In Progress": (1, 0)})
		self.assertEqual({r.label: (r.count, r.client) for r in flow.open_by_priority}["High"], (2, 1))
		self.assertEqual(sum(a.client for a in flow.aging), 1)
		self.assertEqual({r.label: (r.open, r.client) for r in flow.by_tracker}["Task"], (1, 1))
		self.assertEqual(flow.created_waiting, 1)

	def test_waiting_trend_follows_ticking_unticking_and_closing(self):
		"""The waiting-on-client line is rebuilt from the change history."""
		item = self.new_item(MGR, tracker="Task")
		self.assertEqual(get_health(self.ALP, "3m").flow.client_trend[-1], 0)
		self.save_as(MGR, item, dependent_on_client=1)
		self.assertEqual(get_health(self.ALP, "3m").flow.client_trend[-1], 1)
		self.save_as(MGR, item, dependent_on_client=0)
		self.assertEqual(get_health(self.ALP, "3m").flow.client_trend[-1], 0)
		born_waiting = self.waiting()  # ticked when created: no history row, uses 'waiting since'
		self.assertEqual(get_health(self.ALP, "3m").flow.client_trend[-1], 1)
		self.save_as(MGR, born_waiting, status="Closed")
		self.assertEqual(get_health(self.ALP, "3m").flow.client_trend[-1], 0)

	def test_quality_shows_bugs_waiting_on_the_client(self):
		"""Open bugs, their priority split and the critical list mention the client part."""
		self.waiting(tracker="Bug", priority="Urgent", subject="Payment screenshot needed")
		self.new_item(MGR, tracker="Bug", priority="Urgent")
		with self.as_user(TM):
			data = api.get_quality(self.ALP, "3m")
		self.assertEqual((data.tiles.open, data.tiles.client_open), (2, 1))
		self.assertEqual({r.label: (r.count, r.client) for r in data.open_by_priority}["Urgent"], (2, 1))
		self.assertEqual(sorted(c.client for c in data.critical), [0, 1])

	def test_client_dependencies_report(self):
		"""The drill-down report lists waiting tickets, longest wait first, honours filters and visibility."""
		self.waiting(since=2, subject="Recent")
		oldest = self.waiting(since=15, subject="Oldest", note="Signed contract")
		self.new_item(MGR, tracker="Task")  # not waiting
		with self.as_user(TM):
			result = run_report("Client Dependencies", {"project": self.ALP})
		rows = result["result"]
		self.assertEqual(rows[0]["item"], oldest.name)
		self.assertEqual((rows[0]["days_waiting"], rows[0]["note"], len(rows)), (15, "Signed contract", 2))
		with self.as_user(TM):
			filtered = run_report("Client Dependencies", {"project": self.ALP, "min_days": 10})["result"]
		self.assertEqual(len(filtered), 1)
		with self.as_user("out@test.com"):
			self.assertEqual(run_report("Client Dependencies", {})["result"], [])
