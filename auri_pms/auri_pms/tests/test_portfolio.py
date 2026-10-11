"""Portfolio dashboard (all visible projects)."""

import frappe
from frappe.utils import add_days, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TM, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestPortfolio(TrackerTestCase):
	def portfolio(self, user=TM, period="3m"):
		with self.as_user(user):
			data = api.get_portfolio(period)
		return data, {p.name: p for p in data.projects}

	def test_visibility(self):
		"""Managers see every project with an identifier; members their own plus public ones; outsiders public only."""
		_data, tm = self.portfolio(TM)
		self.assertTrue({self.ALP, self.BET} <= set(tm))
		self.assertNotIn(self.GAM, tm)  # no identifier: not part of the portfolio
		_data, out = self.portfolio(OUT)
		self.assertIn(self.BET, out)
		self.assertNotIn(self.ALP, out)
		_data, dev = self.portfolio(DEV)
		self.assertTrue({self.ALP, self.BET} <= set(dev))

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
