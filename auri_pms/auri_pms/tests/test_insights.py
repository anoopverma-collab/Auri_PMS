"""Insights: every dashboard returns the shape the page draws, for one project and for all."""

from collections import Counter

import frappe

from auri_pms.auri_pms import insights
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TrackerTestCase


class TestInsights(TrackerTestCase):
	def test_every_report_has_kpis_visuals_or_a_note(self):
		for key in insights.REPORTS:
			with self.as_user(MGR):
				data = insights.get_insight(key, self.ALP)
			self.assertTrue(data["title"])
			self.assertTrue(data["kpis"] or data.get("note"), key)
			for visual in data["visuals"]:
				self.assertIn(visual["kind"], ("line", "bar", "donut", "stack", "table", "tree"))

	def reports(self):
		"""Every report, for the manager, with some data in it so the visuals are not just empty states."""
		from frappe.utils import add_days, today

		self.new_item(
			MGR, release=self.world.releases["v1"], subject="route a", due_date=add_days(today(), -2)
		)
		self.new_item(MGR, tracker="Bug", subject="route bug", dependent_on_client=1)
		done = self.new_item(MGR, tracker="Task", subject="route done")
		self.save_as(MGR, done, status="Closed")
		for key in insights.REPORTS:
			with self.as_user(MGR):
				yield key, insights.get_insight(key, self.ALP)

	def assert_route(self, route, where):
		self.assertIsInstance(route, dict, where)
		self.assertTrue(route.get("doctype"), where)
		self.assertIsInstance(route.get("filters"), dict, where)

	# KPIs that are a pure label or sentence rather than a count; none today. Add "report:label" with the reason.
	KPI_WITHOUT_ROUTE = ()

	def test_every_kpi_opens_a_list(self):
		for key, data in self.reports():
			for k in data["kpis"]:
				where = f"{key}:{k['label']}"
				if where in self.KPI_WITHOUT_ROUTE:
					continue
				self.assertTrue(k["route"], f"{where} has no route")
				self.assert_route(k["route"], where)

	def test_visual_routes_match_the_data(self):
		"""Every bar, point, donut slice and stack segment carries a route, and the shapes line up with the data."""
		checked = Counter()
		for key, data in self.reports():
			for v in data["visuals"]:
				where = f"{key}:{v['title']}"
				kind = v["kind"]
				if kind in ("bar", "line"):
					self.assertEqual(len(v["routes"]), len(v["datasets"]), where)
					for routes in v["routes"]:
						self.assertEqual(len(routes), len(v["labels"]), where)
						for route in routes:
							self.assert_route(route, where)
				elif kind == "donut":
					self.assertEqual(len(v["routes"]), len(v["labels"]), where)
					self.assertEqual(len(v["values"]), len(v["labels"]), where)
					for route in v["routes"]:
						self.assert_route(route, where)
				elif kind == "stack":
					self.assertEqual(len(v["routes"]), len(v["rows"]), where)
					for row, routes in zip(v["rows"], v["routes"], strict=True):
						self.assertEqual(len(routes), len(row) - 1, where)
						for route in routes:
							self.assert_route(route, where)
					self.assertEqual(len(v.get("row_routes", v["rows"])), len(v["rows"]), where)
					for route in v.get("row_routes", []):
						self.assert_route(route, where)
				elif kind == "table":
					for route in v.get("row_routes", []):
						self.assert_route(route, where)
					if "row_routes" in v:
						self.assertEqual(len(v["row_routes"]), len(v["rows"]), where)
					for row, routes in zip(v["rows"], v.get("cell_routes", v["rows"]), strict=False):
						if "cell_routes" in v:
							self.assertEqual(len(routes), len(row), where)
							for route in routes:
								self.assert_route(route, where)
				checked[kind] += 1
		# the fixture must exercise every chart kind, or the loops above would pass on nothing
		for kind in ("bar", "line", "donut", "stack"):
			self.assertTrue(checked[kind], kind)

	def test_open_backlog_points_open_exactly_the_plotted_tickets(self):
		"""The Open backlog line's links list the tickets that were open then, including ones closed since."""
		from auri_pms.auri_pms.tests.test_quality import days

		first = self.new_item(MGR, tracker="Task", subject="open then closed")
		second = self.new_item(MGR, tracker="Task", subject="still open")
		self.save_as(MGR, first, status="Closed")
		for item in (first, second):
			frappe.db.set_value(
				"Work Item", item.name, "creation", f"{days(-25)} 09:00:00", update_modified=False
			)
		frappe.db.set_value(
			"Work Item", first.name, "closed_on", f"{days(-2)} 12:00:00", update_modified=False
		)
		with self.as_user(MGR):
			data = insights.get_insight("delivery", self.ALP)
		visual = next(v for v in data["visuals"] if v["title"] == "Open backlog")
		points = visual["datasets"][0]["values"]
		routes = visual["routes"][0]
		self.assertEqual(len(routes), len(points))
		for value, route in zip(points, routes, strict=True):
			names = route["filters"]["name"][1]
			self.assertEqual(len([n for n in names if n != "-"]), value)
		self.assertTrue(any(first.name in r["filters"]["name"][1] for r in routes))

	def test_workload_routes_use_the_real_user(self):
		"""A person's row opens the tickets of their email, not of their full name."""
		self.new_item(MGR, assigned_to=DEV, subject="mine")
		with self.as_user(MGR):
			data = insights.get_insight("workload", self.ALP)
		table = next(v for v in data["visuals"] if v["kind"] == "table")
		assigned = {c[0]["filters"]["assigned_to"] for c in table["cell_routes"]}
		self.assertIn(DEV, assigned)

	def test_time_buckets_filter_by_date_range(self):
		for key, data in self.reports():
			if key != "delivery":
				continue
			created = data["visuals"][0]["routes"][0][0]["filters"]["creation"]
			self.assertEqual(created[0], "between")
			self.assertEqual(len(created[1]), 2)

	def test_unknown_report_is_refused(self):
		with self.assertRaises(Exception):
			insights.get_insight("nope")


def walk(node, depth=0, seen=None):
	"""Flatten a Work Breakdown node into (depth, kind) pairs, checking children add up to their parent."""
	seen = [] if seen is None else seen
	seen.append((depth, node["kind"]))
	if node["children"]:
		assert sum(k["tickets"] for k in node["children"]) == node["tickets"], node["label"]
	for kid in node["children"]:
		walk(kid, depth + 1, seen)
	return seen


class TestWorkBreakdown(TrackerTestCase):
	def tree(self, user=MGR, project=None):
		with self.as_user(user):
			data = insights.get_insight("tree", project or self.ALP)
		return data, (data["visuals"][0]["tree"] if data.get("visuals") else [])

	def test_levels_run_project_module_release_sprint_status(self):
		"""A ticket with a release is listed under project > module > release > sprint (backlog) > status."""
		release = self.world.releases["v1"]
		self.new_item(MGR, release=release, subject="deep")
		data, tree = self.tree()
		kinds = []
		for node in tree:
			kinds += walk(node)
		self.assertEqual([k for d, k in kinds if d == 0], ["Project"])
		self.assertEqual({k for d, k in kinds if d == 1}, {"Module"})
		self.assertEqual({k for d, k in kinds if d == 2}, {"Release"})
		self.assertEqual({k for d, k in kinds if d == 3}, {"Sprint"})
		self.assertEqual({k for d, k in kinds if d == 4}, {"Status"})
		self.assertEqual(data["visuals"][0]["kind"], "tree")

	def test_counts_add_up_and_the_kpis_agree(self):
		"""Closed tickets and overdue ones are counted, and the project total equals the Tickets tile."""
		from frappe.utils import add_days, today

		self.new_item(MGR, due_date=add_days(today(), -3), subject="late")
		closed = self.new_item(MGR, tracker="Task", subject="done")
		self.save_as(MGR, closed, status="Closed")
		data, tree = self.tree()
		project = tree[0]
		self.assertEqual(project["tickets"], data["kpis"][0]["value"])
		self.assertEqual(project["closed"], 1)
		self.assertEqual(project["overdue"], 1)
		self.assertEqual(project["pct"], 50)

	def test_items_without_release_or_sprint_are_grouped_last(self):
		"""Tickets with no release go under 'No release' and no sprint under 'Backlog', after the real ones."""
		self.new_item(MGR, release=self.world.releases["v1"], subject="with")
		self.new_item(MGR, subject="without")
		_data, tree = self.tree()
		releases = tree[0]["children"][0]["children"]
		self.assertTrue(releases[-1]["none"])
		self.assertFalse(releases[0]["none"])

	def test_a_user_outside_the_project_gets_no_tree(self):
		"""Nobody sees another project's tickets through the report."""
		self.new_item(MGR, subject="private")
		with self.as_user(OUT):
			with self.assertRaises(Exception):
				insights.get_insight("tree", self.ALP)

	def test_rows_route_to_the_matching_tickets(self):
		"""Every node carries the Work Item filters its count opens."""
		self.new_item(MGR, release=self.world.releases["v1"], subject="route")
		_data, tree = self.tree()
		node = tree[0]["children"][0]["children"][0]
		self.assertEqual(node["route"]["doctype"], "Work Item")
		self.assertEqual(node["route"]["filters"]["release"], self.world.releases["v1"])
