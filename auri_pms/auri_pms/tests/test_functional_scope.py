"""Functional checks of the dashboards' scope and of the pages that were merged or moved.

Covers: the Quality Dashboard across all projects (visibility per user, the setting *Members See All Work Items*, empty
data), the Project dropdown, Delivery & Health against its Health and cost tab (the former Portfolio), and the
sidebar and pages (order, no dead links, the Portfolio redirect).
"""

import json
from pathlib import Path

import frappe
from frappe.desk.search import search_link
from frappe.utils import add_days, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TM, TrackerTestCase, make_project

APP = Path(frappe.get_app_path("auri_pms"))


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestQualityAllProjects(TrackerTestCase):
	"""get_quality with no project: every project the user may see, counted by the database."""

	def bug(self, project=None, user=MGR, created=-1, **kw):
		item = self.new_item(user, project=project, tracker="Bug", **kw)
		frappe.db.set_value(
			"Work Item", item.name, "creation", f"{days(created)} 09:00:00", update_modified=False
		)
		return item

	def quality(self, user=TM, project=None, period="3m"):
		with self.as_user(user):
			return api.get_quality(project, period)

	def by_project(self, data):
		return {row.project: row for row in data.by_project}

	def test_the_all_projects_view_adds_up_every_visible_project(self):
		self.bug(self.ALP)
		self.bug(self.ALP)
		self.bug(self.BET, user=TM)
		everything = self.quality()
		self.assertTrue(everything.has_data)
		rows = self.by_project(everything)
		self.assertEqual((rows[self.ALP].open, rows[self.BET].open), (2, 1))
		# the all-projects numbers are the sum of the numbers of each project
		pms = frappe.get_all("Project", filters={"pms_enabled": 1}, pluck="name")
		per_project = [self.quality(project=p) for p in pms]
		for key in ("open", "closed", "opened_period", "critical_open"):
			self.assertEqual(everything.tiles[key], sum(d.tiles[key] for d in per_project if d.has_data), key)

	def test_the_share_of_bugs_among_new_tickets_counts_all_projects(self):
		before = self.quality().tiles
		self.bug(self.ALP)
		self.new_item(MGR, tracker="Task")
		after = self.quality().tiles
		self.assertEqual(after.opened_period, before.opened_period + 1)
		self.assertGreater(after.bug_share_pct, 0)

	def test_hours_logged_feed_the_bug_density(self):
		self.bug(self.ALP)
		item = self.new_item(MGR, tracker="Task")
		self.logged_time(MGR, work_item=item.name, hours=4)
		tiles = self.quality(project=self.ALP).tiles
		self.assertEqual(tiles.density, round(tiles.opened_period * 100 / 4, 1))

	def test_a_member_sees_their_projects_and_the_public_ones_only(self):
		private = make_project("Project Delta", "DEL", [(MGR, "Manager")])
		self.bug(self.ALP)
		self.bug(private)
		self.bug(self.BET, user=TM)
		dev = self.by_project(self.quality(DEV))
		self.assertIn(self.ALP, dev)  # a member
		self.assertIn(self.BET, dev)  # public
		self.assertNotIn(private, dev)  # neither
		out = self.by_project(self.quality(OUT))
		self.assertIn(self.BET, out)
		self.assertNotIn(self.ALP, out)
		self.assertNotIn(private, out)
		self.assertIn(private, self.by_project(self.quality(TM)))  # an admin sees all

	def test_the_private_project_does_not_change_a_members_totals(self):
		private = make_project("Project Delta", "DEL", [(MGR, "Manager")])
		before = self.quality(DEV).tiles
		self.bug(private)
		self.assertEqual(self.quality(DEV).tiles.open, before.open)
		self.assertEqual(self.quality(DEV).tiles.opened_period, before.opened_period)

	def test_members_see_only_their_own_bugs_when_the_role_box_is_unticked(self):
		mine = self.bug(self.ALP, assigned_to=DEV)
		self.bug(self.ALP)  # somebody else's
		self.set_see_all(True)
		self.assertEqual(self.quality(DEV, self.ALP).tiles.open, 2)
		self.set_see_all(False)
		limited = self.quality(DEV, self.ALP)
		self.assertEqual(limited.tiles.open, 1)
		self.assertEqual(self.quality(MGR, self.ALP).tiles.open, 2)  # a project manager still sees all
		self.assertTrue(mine.name)

	def test_insights_follow_the_role_box_too(self):
		"""Insights reads with raw SQL, so it carries the same condition as the Work Item list."""
		from auri_pms.auri_pms import insights

		self.bug(self.ALP, assigned_to=DEV)
		self.bug(self.ALP)

		def open_total():
			with self.as_user(DEV):
				kpis = insights.get_insight("delivery", self.ALP)["kpis"]
			return next(
				k["value"]
				for k in kpis
				if "pen" in str(k["label"]).lower() or "open" in str(k["label"]).lower()
			)

		self.set_see_all(True)
		everything = int(open_total())
		self.set_see_all(False)
		self.assertLess(int(open_total()), everything)

	def test_a_project_without_tickets_gives_an_empty_dashboard(self):
		empty = make_project("Project Delta", "DEL", [(MGR, "Manager")])
		data = self.quality(MGR, empty)
		self.assertFalse(data.has_data)
		self.assertEqual(data.tiles.open, 0)

	def test_without_a_defect_tracker_the_dashboard_says_so(self):
		for name in frappe.get_all("Ticket Type", filters={"is_defect": 1}, pluck="name"):
			frappe.db.set_value("Ticket Type", name, "is_defect", 0)
		data = self.quality()
		self.assertFalse(data.has_data)
		self.assertEqual(list(data.defect_trackers), [])

	def test_every_period_works_for_all_projects(self):
		self.bug(self.ALP, created=-40)
		for period in ("1m", "3m", "6m", "all"):
			data = self.quality(period=period)
			self.assertEqual(data.period, period)
			self.assertEqual(len(data.flow.opened), len(data.labels))

	def test_the_project_dropdown_lists_only_projects_with_auri_pms(self):
		def listed(user):
			with self.as_user(user):
				return {r["value"] for r in search_link("Project", "", filters={"pms_enabled": 1})}

		tm = listed(TM)
		self.assertTrue({self.ALP, self.BET} <= tm)
		self.assertNotIn(self.GAM, tm)  # Auri PMS is off there
		dev = listed(DEV)
		self.assertIn(self.ALP, dev)
		self.assertNotIn(self.GAM, dev)
		out = listed(OUT)
		self.assertIn(self.BET, out)  # public
		self.assertNotIn(self.ALP, out)  # not allocated


class TestProjectScopeEverywhere(TrackerTestCase):
	"""Only projects with Auri PMS switched on are offered or counted, in every picker and dashboard."""

	def test_every_project_link_of_the_app_is_limited_to_auri_pms_projects(self):
		"""Doctype fields carry a link filter; page, report and calendar fields carry a get_query."""
		missing = []
		for path in (APP / "auri_pms/doctype").glob("*/*.json"):
			doc = json.loads(path.read_text())
			if doc.get("doctype") != "DocType":
				continue
			for field in doc.get("fields", []):
				if field.get("fieldtype") == "Link" and field.get("options") == "Project":
					if "pms_enabled" not in (field.get("link_filters") or ""):
						missing.append(f"{path.parent.name}.{field['fieldname']}")
		for path in [
			*(APP / "auri_pms/page").glob("*/*.js"),
			*(APP / "auri_pms/report").glob("*/*.js"),
			*(APP / "auri_pms/doctype").glob("*/*calendar.js"),
		]:
			text = path.read_text()
			for line in text.splitlines():
				if (
					'options: "Project"' in line
					and "get_query" not in text.split(line)[1][:200]
					and "get_query" not in line
				):
					missing.append(path.name)
		self.assertEqual(missing, [])

	def test_quality_leaves_out_a_project_that_was_switched_off(self):
		"""A project switched off after it got records keeps them, but they leave the Quality Dashboard."""
		switched_off = make_project("Project Delta", "DEL", [(MGR, "Manager")])
		self.new_item(MGR, project=switched_off, tracker="Bug")
		with self.as_user(TM):
			before = api.get_quality(None, "3m").by_project
		self.assertIn(switched_off, [r.project for r in before])
		frappe.db.set_value("Project", switched_off, "pms_enabled", 0)
		with self.as_user(TM):
			after = api.get_quality(None, "3m")
			self.assertNotIn(switched_off, [r.project for r in after.get("by_project") or []])
			with self.assertRaises(frappe.PermissionError):
				api.get_quality(switched_off, "3m")

	def test_every_dashboard_lists_the_same_pms_projects_for_an_admin(self):
		pms = set(frappe.get_all("Project", filters={"pms_enabled": 1}, pluck="name"))
		with self.as_user(TM):
			from auri_pms.auri_pms import insights

			self.assertEqual(set(insights.get_insight_projects()), pms)
			self.assertEqual({p["name"] for p in api.get_management_dashboard()["projects"]}, pms)
			self.assertEqual({p.name for p in api.get_portfolio("3m").projects}, pms)
			self.assertEqual({p.name for p in api.get_hub_projects()}, pms)


class TestInsightsScope(TrackerTestCase):
	"""Auri Insights covers the projects the user is allocated to (all of them for an admin), not every readable project."""

	def projects(self, user):
		from auri_pms.auri_pms import insights

		with self.as_user(user):
			return set(insights.get_insight_projects())

	def test_a_member_gets_their_projects_only(self):
		self.assertIn(self.ALP, self.projects(DEV))
		self.assertNotIn(self.BET, self.projects(DEV))  # public, but not allocated
		self.assertNotIn(self.GAM, self.projects(DEV))  # Auri PMS is off there

	def test_a_manager_gets_the_projects_they_are_on(self):
		self.assertTrue({self.ALP, self.BET} <= self.projects(MGR))

	def test_an_admin_gets_every_pms_project(self):
		pms = set(frappe.get_all("Project", filters={"pms_enabled": 1}, pluck="name"))
		self.assertEqual(self.projects(TM), pms)

	def test_someone_with_no_allocation_gets_none(self):
		self.assertEqual(self.projects(OUT), set())

	def test_every_report_covers_only_those_projects(self):
		from auri_pms.auri_pms import insights

		private = make_project("Project Delta", "DEL", [(MGR, "Manager")])
		self.new_item(MGR, project=private, tracker="Bug")
		with self.as_user(DEV):
			for key in insights.REPORTS:
				data = insights.get_insight(key)
				self.assertIn(
					"1 project", data["subtitle"], key
				)  # Alpha only; Beta (public) and Delta are not counted

	def test_a_project_outside_the_scope_is_refused(self):
		from auri_pms.auri_pms import insights

		for user, project in ((DEV, self.BET), (OUT, self.ALP), (DEV, self.GAM)):
			with self.as_user(user), self.assertRaises(frappe.PermissionError):
				insights.get_insight("delivery", project)

	def test_someone_with_no_allocation_sees_an_empty_dashboard_not_an_error(self):
		from auri_pms.auri_pms import insights

		with self.as_user(OUT):
			for key in insights.REPORTS:
				insights.get_insight(key)


class TestHealthAndCostTab(TrackerTestCase):
	"""The Portfolio now lives in Delivery & Health; both read the same projects and agree on the numbers."""

	def both(self, user):
		with self.as_user(user):
			return api.get_portfolio("3m"), api.get_management_dashboard()

	def test_both_views_list_the_same_projects(self):
		for user in (TM, MGR):
			health, management = self.both(user)
			self.assertEqual(
				{p.name for p in health.projects}, {p["name"] for p in management["projects"]}, user
			)

	def test_both_views_agree_on_the_ticket_numbers(self):
		self.new_item(MGR, tracker="Task", due_date=days(-3))
		self.new_item(MGR, tracker="Task")
		for user in (TM, MGR):
			health, management = self.both(user)
			k, m = health.kpis, management["kpis"]
			self.assertEqual(k.projects, m["projects"], user)
			self.assertEqual(k.open, m["tasks_open"], user)
			self.assertEqual(k.overdue, m["tasks_overdue"], user)
			self.assertEqual(k.closed, m["tasks_completed"], user)

	def test_the_same_users_are_refused_by_both(self):
		for user in (OUT,):
			with self.as_user(user):
				with self.assertRaises(frappe.PermissionError):
					api.get_portfolio("3m")
				with self.assertRaises(frappe.PermissionError):
					api.get_management_dashboard()

	def test_the_health_tab_boot_flag_matches_the_dashboard_access(self):
		from auri_pms.auri_pms.utils import portfolio_projects

		for user, allowed in ((TM, True), (MGR, True), (DEV, True), (OUT, False)):
			with self.as_user(user):
				self.assertEqual(bool(portfolio_projects()), allowed, user)


class TestSidebarAndPages(TrackerTestCase):
	FILES = ("workspace_sidebar/auri_pms.json", "auri_pms/sidebar/auri_pms/auri_pms.json")

	def items(self, path):
		return json.loads((APP / path).read_text())["items"]

	def test_both_sidebar_files_have_the_same_order(self):
		first, second = ([i["label"] for i in self.items(f)] for f in self.FILES)
		self.assertEqual(first, second)

	def test_insights_and_the_management_dashboard_come_first_and_the_portfolio_is_gone(self):
		for path in self.FILES:
			links = [i.get("link_to") for i in self.items(path)]
			self.assertEqual(links[:3], ["pms-insights", "management-dashboard", "status-report"], path)
			for gone in (
				"portfolio",
				"project-hub",
				"quality-dashboard",
			):  # the pages still exist; the sidebar does not list them
				self.assertNotIn(gone, links, path)

	def test_the_installed_sidebar_matches_the_file(self):
		shipped = [i.get("link_to") or "" for i in self.items(self.FILES[0])]
		installed = [i.link_to or "" for i in frappe.get_doc("Workspace Sidebar", "Auri PMS").items]
		self.assertEqual(installed, shipped)

	def test_every_sidebar_link_opens_something(self):
		kinds = {"Page": "Page", "DocType": "DocType", "Report": "Report"}
		for path in self.FILES:
			for item in self.items(path):
				if item.get("type") != "Link":
					continue
				kind = kinds.get(item["link_type"])
				self.assertTrue(kind, f"{item['label']}: unknown link type {item['link_type']}")
				self.assertTrue(
					frappe.db.exists(kind, item["link_to"]), f"{path}: {item['label']} points nowhere"
				)

	def test_the_dashboard_pages_exist_for_the_pms_roles(self):
		for page in (
			"management-dashboard",
			"portfolio",
			"quality-dashboard",
			"pms-insights",
			"project-hub",
			"my-work",
		):
			roles = {r.role for r in frappe.get_doc("Page", page).roles}
			self.assertIn("Auri PMS User", roles, page)

	def test_the_old_portfolio_route_redirects_to_the_health_tab(self):
		script = (APP / "auri_pms/page/portfolio/portfolio.js").read_text()
		self.assertIn('tab: "health"', script)
		self.assertIn('set_route("management-dashboard")', script)
		self.assertNotIn("class Portfolio", script)  # the view lives in the bundle now

	def test_the_dashboard_loads_the_health_bundle_that_exists(self):
		bundle = APP / "public/js/auri_portfolio.bundle.js"
		self.assertTrue(bundle.exists())
		self.assertIn("auri_pms.Portfolio = Portfolio", bundle.read_text())
		page = (APP / "auri_pms/page/management_dashboard/management_dashboard.js").read_text()
		self.assertIn("auri_portfolio.bundle.js", page)
		self.assertIn("auri_pms.Portfolio", page)

	def test_the_project_hub_buttons_open_the_dashboard(self):
		hub = (APP / "auri_pms/page/project_hub/project_hub.js").read_text()
		self.assertNotIn('set_route("portfolio")', hub)
		self.assertIn('set_route("management-dashboard")', hub)
