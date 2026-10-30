"""Project dashboard snapshots: one record per project, day and type, with the figures and the full data."""

import json

import frappe
from frappe.utils import add_days, today

from auri_pms.auri_pms import snapshots
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TrackerTestCase


class TestSnapshots(TrackerTestCase):
	def test_snapshot_keeps_figures_and_full_data(self):
		name = snapshots.take_snapshot(self.ALP, "Weekly")
		doc = frappe.get_doc("Project Dashboard Snapshot", name)
		health = json.loads(doc.data)
		self.assertEqual(doc.project, self.ALP)
		self.assertEqual(doc.open_tickets, health["flow"]["open"])
		self.assertEqual(doc.period_type, "Weekly")

	def test_same_day_and_type_replaces_the_snapshot(self):
		first = snapshots.take_snapshot(self.ALP, "Manual")
		self.assertEqual(snapshots.take_snapshot(self.ALP, "Manual"), first)
		self.assertNotEqual(snapshots.take_snapshot(self.ALP, "Manual", add_days(today(), -7)), first)

	def test_history_lists_newest_first(self):
		snapshots.take_snapshot(self.ALP, "Manual", add_days(today(), -7))
		snapshots.take_snapshot(self.ALP, "Manual")
		with self.as_user(MGR):
			dates = [str(r.snapshot_date) for r in snapshots.get_project_snapshots(self.ALP)]
		self.assertEqual(dates, sorted(dates, reverse=True))

	def test_scheduled_run_covers_enabled_projects(self):
		self.assertIn(self.ALP, snapshots.enabled_projects())

	def test_delete_needs_allocation(self):
		name = snapshots.take_snapshot(self.ALP, "Manual")
		with self.as_user(OUT):
			with self.assertRaises(frappe.PermissionError):
				snapshots.delete_project_snapshot(name)
		with self.as_user(MGR):
			snapshots.delete_project_snapshot(name)
		self.assertFalse(frappe.db.exists("Project Dashboard Snapshot", name))


class TestSnapshotVisibility(TrackerTestCase):
	def test_a_snapshot_is_only_visible_to_members_of_its_project(self):
		snap = frappe.get_doc(
			{"doctype": "Project Dashboard Snapshot", "project": self.ALP, "snapshot_date": today()}
		).insert(ignore_permissions=True)
		with self.as_user(DEV):
			self.assertIn(snap.name, frappe.get_list("Project Dashboard Snapshot", pluck="name"))
		with self.as_user(OUT):
			self.assertNotIn(snap.name, frappe.get_list("Project Dashboard Snapshot", pluck="name"))
			self.assertFalse(frappe.has_permission("Project Dashboard Snapshot", "read", doc=snap.name))
