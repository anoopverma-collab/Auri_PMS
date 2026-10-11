"""Quality dashboard (defects)."""

import frappe
from frappe.utils import add_days, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.dashboards import get_quality_data
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TM, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestQuality(TrackerTestCase):
	def bug(self, created=-1, closed=None, **kw):
		"""Create a Bug; optionally close it and back-date creation/closing."""
		item = self.new_item(MGR, tracker=kw.pop("tracker", "Bug"), **kw)
		if closed is not None:
			self.save_as(TM, item, status="Closed")  # the Bug workflow lets only a manager close a new bug
			frappe.db.set_value(
				"Work Item", item.name, "closed_on", f"{days(closed)} 12:00:00", update_modified=False
			)
		frappe.db.set_value(
			"Work Item", item.name, "creation", f"{days(created)} 09:00:00", update_modified=False
		)
		item.reload()
		return item

	def quality(self, project=None, period="3m", user=TM):
		with self.as_user(user):
			return api.get_quality(project or self.ALP, period)

	def test_bug_is_a_defect_tracker(self):
		"""The shipped Bug tracker is flagged as a defect tracker; others are not."""
		flags = dict(frappe.get_all("Ticket Type", fields=["name", "is_defect"], as_list=True))
		self.assertEqual((flags["Bug"], flags["Task"], flags["Feature"]), (1, 0, 0))

	def test_counts_and_share(self):
		"""Open/closed bugs, bugs opened in the period and their share of all new tickets."""
		self.bug(-5)
		self.bug(-4, closed=-1)
		self.new_item(MGR, tracker="Task")
		self.new_item(MGR, tracker="Feature")
		tiles = self.quality().tiles
		self.assertEqual((tiles.open, tiles.closed, tiles.opened_period, tiles.fixed_period), (1, 1, 2, 1))
		self.assertEqual(tiles.bug_share_pct, 50)  # 2 bugs of 4 new tickets

	def test_opened_vs_fixed_series(self):
		"""Weekly opened and fixed series add up to the period totals."""
		self.bug(-20, closed=-10)
		self.bug(-2)
		data = self.quality()
		self.assertEqual(sum(data.flow.opened), 2)
		self.assertEqual(sum(data.flow.fixed), 1)
		self.assertEqual(len(data.flow.opened), len(data.labels))

	def test_fix_time_by_priority(self):
		"""Mean days from opening to closing, per priority."""
		self.bug(-10, closed=-4, priority="High")
		self.bug(-8, closed=-4, priority="High")
		self.bug(-3, closed=-1, priority="Low")
		data = self.quality()
		by = {r.priority: (r.days, r.count) for r in data.fix_time}
		self.assertEqual(by, {"High": (5.0, 2), "Low": (2.0, 1)})
		self.assertEqual(data.tiles.avg_fix_days, 4.0)

	def test_reopen_rate_from_history(self):
		"""A bug moved from Closed back to an open status counts as reopened."""
		first, second, third = self.bug(-6), self.bug(-6), self.bug(-6)
		for bug in (first, second, third):
			self.save_as(TM, bug, status="Closed")
		self.save_as(TM, first, status="In Progress")  # reopened
		tiles = self.quality().tiles
		self.assertEqual((tiles.reopened, tiles.reopen_rate), (1, 33.3))

	def test_critical_open_bugs_drive_the_status(self):
		"""Old critical bugs make the area red and are listed; fresh ones are amber."""
		self.bug(-10, priority="Urgent", subject="Payments fail")
		data = self.quality()
		self.assertEqual(data.status.level, "red")
		self.assertEqual(data.tiles.critical_open, 1)
		self.assertEqual((data.critical[0].subject, data.critical[0].age_days), ("Payments fail", 10))

	def test_amber_for_a_fresh_critical_bug(self):
		"""A critical bug opened recently is a warning, not an alarm."""
		self.bug(-1, priority="Immediate")
		self.assertEqual(self.quality().status.level, "amber")

	def test_green_when_clean(self):
		"""No critical bugs, no reopens: Healthy."""
		self.bug(-2, closed=-1)
		status = self.quality().status
		self.assertEqual((status.level, status.label), ("green", "Healthy"))

	def test_defect_density(self):
		"""Bugs opened per 100 hours spent."""
		item = self.bug(-2)
		self.logged_time(DEV, item.name, 4)
		self.assertEqual(self.quality().tiles.density, 25.0)  # 1 bug / 4 hours

	def test_categories(self):
		"""Bugs per category use the category's display name."""
		with self.as_user(MGR):
			category = frappe.get_doc(
				{"doctype": "Work Item Category", "category_name": "Checkout", "project": self.ALP}
			).insert()
		self.bug(-2, category=category.name)
		self.bug(-2, category=category.name)
		self.bug(-2)
		by = {r.label: (r.open, r.closed) for r in self.quality().by_category}
		self.assertEqual(by["Checkout"], (2, 0))

	def test_all_projects_view_lists_projects(self):
		"""Without a project the dashboard covers every visible project and lists them."""
		self.bug(-2)
		with self.as_user(TM):
			data = api.get_quality(None, "3m")
		self.assertTrue(data.by_project)
		self.assertIn(self.ALP, [r.project for r in data.by_project])

	def test_access(self):
		"""Outsiders cannot open a private project's quality data and see only public data overall."""
		self.bug(-2)
		self.assertRaises(frappe.PermissionError, self.quality, self.ALP, "3m", OUT)
		with self.as_user(OUT):
			data = api.get_quality(None, "3m")
		self.assertNotIn(self.ALP, [r.project for r in (data.by_project or [])])

	def test_no_defect_tracker(self):
		"""Without any defect tracker the dashboard says so instead of failing."""
		frappe.db.set_value("Ticket Type", "Bug", "is_defect", 0)
		data = get_quality_data(self.ALP, "3m")
		self.assertFalse(data.has_data)
		self.assertEqual(data.defect_trackers, [])
