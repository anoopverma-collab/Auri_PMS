"""API behind the Desk UI: link queries, status actions, dashboard connections, Gantt events."""

import json

import frappe
from frappe.desk.calendar import get_events

from auriga_track.tracking import api
from auriga_track.tracking.project_hooks import get_dashboard_data
from auriga_track.tracking.tests.utils import DEV, GONE, MGR, OUT, REP, TrackerTestCase


class TestUiApi(TrackerTestCase):
	def test_status_query_includes_current_and_allowed(self):
		"""The status field offers the current status plus the allowed next statuses."""
		item = self.new_item(DEV)
		with self.as_user(DEV):
			rows = api.status_query("Work Item Status", "", "name", 0, 20, {"work_item": item.name})
		self.assertEqual([r[0] for r in rows], ["New", "In Progress"])

	def test_status_actions_for_close_and_reopen(self):
		"""Close/Reopen buttons: open items offer Close, closed items offer Reopen."""
		item = self.new_item(MGR, tracker="Task")
		with self.as_user(MGR):
			self.assertEqual(api.get_status_actions(item.name), {"close": "Closed", "reopen": None})
		self.save_as(MGR, item, status="Closed")
		with self.as_user(MGR):
			self.assertEqual(api.get_status_actions(item.name), {"close": None, "reopen": "New"})

	def test_tracker_query_respects_enabled_trackers(self):
		"""Only trackers enabled on the project are offered; empty list means all active ones."""
		with self.as_user(MGR):
			bet = {r[0] for r in api.tracker_query("Ticket Type", "", "name", 0, 20, {"project": self.BET})}
			alp = {r[0] for r in api.tracker_query("Ticket Type", "", "name", 0, 20, {"project": self.ALP})}
		self.assertEqual(bet, {"Bug", "Task"})
		self.assertEqual(alp, {"Bug", "Feature", "Task", "Support"})

	def test_assignee_query_only_assignable_members(self):
		"""Only enabled members whose role can be assigned are offered (not rep, not the disabled user)."""
		with self.as_user(MGR):
			users = {r[0] for r in api.assignee_query("User", "", "name", 0, 20, {"project": self.ALP})}
		self.assertEqual(users, {MGR, DEV})
		self.assertNotIn(GONE, users)

	def test_parent_query_excludes_self_and_descendants(self):
		"""Parent choices exclude the item itself and its descendants."""
		root = self.new_item(MGR)
		child = self.new_item(MGR, parent_work_item=root.name)
		other = self.new_item(MGR)
		with self.as_user(MGR):
			rows = api.parent_query(
				"Work Item", "", "name", 0, 20, {"project": self.ALP, "work_item": root.name}
			)
		self.assertEqual({r[0] for r in rows}, {other.name})
		self.assertNotIn(child.name, {r[0] for r in rows})

	def test_project_create_query(self):
		"""Projects without identifier or without can_create_items are not offered."""
		with self.as_user(REP):
			rows = {r[0] for r in api.project_create_query("Project", "", "name", 0, 20, {})}
		self.assertIn(self.ALP, rows)
		self.assertIn(self.BET, rows)  # public project, Reporter may create
		self.assertNotIn(self.GAM, rows)
		with self.as_user(OUT):
			rows = {r[0] for r in api.project_create_query("Project", "", "name", 0, 20, {})}
		self.assertEqual(rows, {self.BET})

	def test_log_time_api(self):
		"""log_time creates a Time Entry for the session user."""
		item = self.new_item(MGR)
		with self.as_user(DEV):
			name = api.log_time(item.name, 1.5, "Testing", comment="API")
		entry = frappe.get_doc("Time Entry", name)
		self.assertEqual((entry.user, entry.hours, entry.work_item), (DEV, 1.5, item.name))

	def test_dashboard_connections(self):
		"""The Project dashboard gets a Tracker group with Work Items, Releases and Time Entries."""
		data = get_dashboard_data({"fieldname": "project", "transactions": []})
		self.assertIn(
			{"label": "Tracker", "items": ["Work Item", "Release", "Time Entry"]}, data["transactions"]
		)
		hooked = frappe.get_hooks("override_doctype_dashboards")["Project"]
		self.assertIn("auriga_track.tracking.project_hooks.get_dashboard_data", hooked)

	def test_work_item_connections_and_onload(self):
		"""The Work Item form links Subtasks and Time Entries; onload flags items with children."""
		parent = self.new_item(MGR)
		self.new_item(MGR, parent_work_item=parent.name)
		doc = frappe.get_doc("Work Item", parent.name)
		doc.run_method("onload")
		self.assertTrue(doc.get_onload("has_children"))
		links = {(l.link_doctype, l.link_fieldname) for l in frappe.get_meta("Work Item").links}
		self.assertEqual(links, {("Work Item", "parent_work_item"), ("Time Entry", "work_item")})

	def test_gantt_events_use_start_and_due_dates(self):
		"""Gantt/Calendar field map: start_date -> start, due_date -> end, subject -> title."""
		item = self.new_item(MGR, start_date="2026-10-01", due_date="2026-10-20", subject="Gantt bar")
		with self.as_user(MGR):
			events = get_events(
				"Work Item",
				"2026-10-01",
				"2026-10-31",
				field_map=json.dumps(
					{"start": "start_date", "end": "due_date", "id": "name", "title": "subject"}
				),
			)
		self.assertIn(item.name, {e["name"] for e in events})

	def test_status_indicators(self):
		"""Status colours map to the nearest Desk indicator; the API returns one entry per status."""
		from auriga_track.tracking.utils import nearest_indicator

		self.assertEqual(nearest_indicator("#2490EF"), "blue")
		self.assertEqual(nearest_indicator("#fe9a1b"), "orange")
		self.assertEqual(nearest_indicator(None), "gray")
		self.assertEqual(nearest_indicator("not-a-colour"), "gray")
		with self.as_user(DEV):
			indicators = api.get_status_indicators()
		self.assertEqual(indicators["New"], "blue")
		self.assertEqual(indicators["Closed"], "green")
		self.assertEqual(set(indicators), set(frappe.get_all("Work Item Status", pluck="name")))

	def test_awesome_bar_search_indexes_and_respects_visibility(self):
		"""Work Items are indexed for global search; the read check Awesome Bar applies hides them from outsiders."""
		from frappe.utils.global_search import sync_global_search

		item = self.new_item(MGR, subject="Zebrafish login problem")
		sync_global_search()
		rows = frappe.db.sql(
			"select content from __global_search where doctype = 'Work Item' and name = %s", item.name
		)
		self.assertIn("Zebrafish", " ".join(r[0] for r in rows))
		self.assertTrue(frappe.has_permission("Work Item", "read", doc=item.name, user=MGR))
		self.assertFalse(frappe.has_permission("Work Item", "read", doc=item.name, user=OUT))
		self.assertIn(
			"Work Item", [d["doctype"] for d in frappe.get_hooks("global_search_doctypes")["Default"]]
		)
