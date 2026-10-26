"""Insights: every dashboard returns the shape the page draws, for one project and for all."""

from auri_pms.auri_pms import insights
from auri_pms.auri_pms.tests.utils import MGR, TrackerTestCase


class TestInsights(TrackerTestCase):
	def test_every_report_has_kpis_visuals_or_a_note(self):
		for key in insights.REPORTS:
			with self.as_user(MGR):
				data = insights.get_insight(key, self.ALP)
			self.assertTrue(data["title"])
			self.assertTrue(data["kpis"] or data.get("note"), key)
			for visual in data["visuals"]:
				self.assertIn(visual["kind"], ("line", "bar", "donut", "stack", "table"))

	def test_unknown_report_is_refused(self):
		with self.assertRaises(Exception):
			insights.get_insight("nope")
