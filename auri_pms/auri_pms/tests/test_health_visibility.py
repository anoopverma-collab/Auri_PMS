"""Per-project switches that show or hide the health status on each screen."""

import frappe

from auri_pms.auri_pms import api
from auri_pms.auri_pms.health import health_visible
from auri_pms.auri_pms.status_report import build_report, render_html
from auri_pms.auri_pms.tests.utils import MGR, TM, TrackerTestCase, ensure_company

FLAGS = ("show_health_hub", "show_health_portfolio", "show_health_report")


class TestHealthVisibility(TrackerTestCase):
	def hide(self, *flags):
		for flag in flags:
			frappe.db.set_value("Project", self.ALP, flag, 0)

	def window(self):
		from frappe.utils import add_days, today

		return add_days(today(), -7), today()

	def test_default_is_hidden_everywhere(self):
		"""A project that never touched the switches shows no health status on any screen."""
		fresh = frappe.get_doc(
			{"doctype": "Project", "company": ensure_company(), "project_name": "Switch default"}
		).insert(ignore_permissions=True)
		for screen in ("hub", "portfolio", "report"):
			self.assertFalse(health_visible(fresh.name, screen), screen)
		self.assertTrue(all(not frappe.db.get_value("Project", fresh.name, f) for f in FLAGS))
		self.assertTrue(all(health_visible(self.ALP, s) for s in ("hub", "portfolio", "report")))

	def test_hub_switch_hides_only_the_hub_status(self):
		self.hide("show_health_hub")
		with self.as_user(MGR):
			data = api.get_project_health(self.ALP, "3m")
		self.assertIsNone(data.status)
		self.assertIn("flow", data)  # the numbers and charts stay
		with self.as_user(TM):
			rows = {p.name: p for p in api.get_portfolio("3m").projects}
		self.assertNotEqual(rows[self.ALP].label, "Hidden")

	def test_portfolio_switch_hides_the_verdict_not_the_numbers(self):
		self.new_item(MGR, tracker="Task")
		self.hide("show_health_portfolio")
		with self.as_user(TM):
			data = api.get_portfolio("3m")
		row = {p.name: p for p in data.projects}[self.ALP]
		self.assertEqual((row.level, row.label, row.score, row.headline), ("none", "Hidden", None, ""))
		self.assertGreaterEqual(row.open, 1)
		# hidden projects stay out of the health mix: they are neither off track, at risk, on track nor "no data"
		self.assertTrue(row.health_hidden)
		self.assertEqual(row.reason_list, [])
		self.assertTrue(all(p.health_hidden or isinstance(p.reason_list, list) for p in data.projects))
		self.assertGreaterEqual(data.kpis["hidden"], 1)
		self.assertEqual(
			data.kpis["red"]
			+ data.kpis["amber"]
			+ data.kpis["green"]
			+ data.kpis["none"]
			+ data.kpis["hidden"],
			data.kpis["projects"],
		)
		with self.as_user(MGR):
			self.assertIsNotNone(api.get_project_health(self.ALP, "3m").status)

	def test_report_switch_removes_the_status_block(self):
		start, end = self.window()
		shown = build_report(self.ALP, start, end)
		self.assertIsNotNone(shown.status)
		html = render_html(shown)
		client = ("On track", "On track, with a few items to watch", "Needs attention", "No data yet")
		self.assertTrue(any(f">{label}<" in html or f"{label}</" in html for label in client))
		if shown.status.label not in client:  # "No data yet" reads the same to both
			self.assertNotIn(shown.status.label, html)  # the internal label ("At Risk", "Off Track") stays with the team
		self.hide("show_health_report")
		hidden = build_report(self.ALP, start, end)
		self.assertIsNone(hidden.status)
		html = render_html(hidden)
		self.assertFalse(any(f">{label}<" in html or f"{label}</" in html for label in client))
		self.assertIn("Delivered", html)  # the rest of the report is unchanged
		with self.as_user(MGR):
			preview = api.get_status_report_html(self.ALP, start, end)
		self.assertIsNone(preview["status"])
