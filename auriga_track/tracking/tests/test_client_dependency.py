"""Tickets that depend on the client: the checkbox, its counts and where they show up."""

import frappe
from frappe.desk.query_report import run as run_report
from frappe.utils import add_days, today

from auriga_track.tracking import api
from auriga_track.tracking.dashboards import get_my_work_data
from auriga_track.tracking.health import get_health
from auriga_track.tracking.status_report import build_report, render_html
from auriga_track.tracking.tests.utils import DEV, MGR, TM, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestClientDependency(TrackerTestCase):
	def waiting(self, since=0, note="Please send the logo files", **kw):
		"""A ticket that depends on the client, optionally back-dated."""
		item = self.new_item(MGR, tracker="Task", dependent_on_client=1, client_dependency_note=note, **kw)
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
