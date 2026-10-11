"""Project Module: a per-project list of product areas that tickets can be tagged with."""

import frappe
from frappe.utils import add_days, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.status_report import build_report, render_html
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TM, TrackerTestCase


class TestProjectModule(TrackerTestCase):
	def make_module(self, name="Sales", user=MGR, project=None):
		with self.as_user(user):
			return frappe.get_doc(
				{"doctype": "Project Module", "module_name": name, "project": project or self.ALP}
			).insert()

	def test_name_is_project_and_module(self):
		self.assertEqual(self.make_module("Stock").name, f"{self.ALP}-Stock")

	def test_only_project_managers_maintain_modules(self):
		self.assertThrows("not allowed to manage modules", lambda: self.make_module("Dev made", user=DEV))
		self.assertThrows("not allowed to manage modules", lambda: self.make_module("Out made", user=OUT))

	def test_work_item_module_must_belong_to_the_same_project(self):
		other = self.make_module("Beta module", project=self.BET)
		self.assertThrows(
			"does not belong to Project",
			lambda: self.new_item(MGR, tracker="Task", project_module=other.name),
		)
		mine = self.make_module("Accounts")
		item = self.new_item(MGR, tracker="Task", project_module=mine.name)
		self.assertEqual(item.project_module, mine.name)

	def test_hub_and_health_break_open_tickets_down_by_module(self):
		sales, stock = self.make_module("Sales"), self.make_module("Stock")
		self.new_item(MGR, tracker="Task", project_module=sales.name)
		self.new_item(MGR, tracker="Task", project_module=sales.name)
		closed = self.new_item(MGR, tracker="Task", project_module=stock.name)
		self.save_as(MGR, closed, status="Closed")
		self.new_item(MGR, tracker="Task")  # no module
		with self.as_user(TM):
			hub = api.get_project_hub(self.ALP)
			health = api.get_project_health(self.ALP, "3m")
		self.assertEqual([(r["label"], r["count"]) for r in hub.by_module][:1], [("Sales", 2)])
		self.assertEqual(hub.by_module[-1]["label"], "(no module)")
		rows = {r["label"]: r for r in health.flow.by_module}
		self.assertEqual((rows["Sales"]["open"], rows["Sales"]["closed"]), (2, 0))
		self.assertEqual((rows["Stock"]["open"], rows["Stock"]["closed"]), (0, 1))

	def test_quality_dashboard_groups_bugs_by_module(self):
		sales = self.make_module("Sales")
		self.new_item(MGR, tracker="Bug", project_module=sales.name)
		self.new_item(MGR, tracker="Bug")
		with self.as_user(TM):
			data = api.get_quality(self.ALP, "3m")
		labels = {r["label"]: r for r in data.by_module}
		self.assertEqual(labels["Sales"]["open"], 1)
		self.assertEqual(labels["(no module)"]["open"], 1)

	def test_my_work_rows_carry_the_module_name(self):
		sales = self.make_module("Sales")
		self.new_item(MGR, tracker="Task", project_module=sales.name, assigned_to=DEV)
		with self.as_user(DEV):
			data = api.get_my_work()
		rows = [i for group in data.groups.values() for i in group]
		self.assertEqual([i["module"] for i in rows if i["project_module"]], ["Sales"])

	def test_client_report_shows_modules(self):
		sales = self.make_module("Sales")
		self.new_item(MGR, tracker="Task", project_module=sales.name, subject="Module ticket")
		report = build_report(self.ALP, add_days(today(), -7), today())
		self.assertEqual([(m["label"], m["open"]) for m in report.modules], [("Sales", 1)])
		html = render_html(report)
		self.assertIn("Progress by module", html)
		self.assertIn("Sales", html)

	def test_client_report_has_no_module_table_when_nothing_is_tagged(self):
		self.new_item(MGR, tracker="Task")
		report = build_report(self.ALP, add_days(today(), -7), today())
		self.assertEqual(report.modules, [])
		self.assertNotIn("Progress by module", render_html(report))
