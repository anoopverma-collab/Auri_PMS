"""Non-functional checks (spec section 9): indexes and performance targets."""

import time

import frappe
from frappe.utils import now

from auri_pms.auri_pms.tests.utils import DEV, MGR, TrackerTestCase, ensure_company

WORK_ITEM_INDEXES = ("project", "status", "assigned_to", "parent_work_item", "release", "is_closed")
TIME_ENTRY_INDEXES = ("work_item", "user", "date")


class TestPerformance(TrackerTestCase):
	def test_indexes_exist(self):
		"""project, status, assigned_to, parent_work_item, release, is_closed / work_item, user, date are indexed."""
		for doctype, columns in (("Work Item", WORK_ITEM_INDEXES), ("Time Entry", TIME_ENTRY_INDEXES)):
			indexed = {row[4] for row in frappe.db.sql(f"show index from `tab{doctype}`")}
			for column in columns:
				self.assertIn(column, indexed, f"{doctype}.{column}")

	def test_list_load_with_10000_items_under_two_seconds(self):
		"""A Tracker User opens the Work Item list with 10,000 items in 50 projects in under 2 seconds."""
		projects = [self.ALP, self.BET]
		for number in range(48):
			doc = frappe.get_doc(
				{
					"doctype": "Project",
					"company": ensure_company(),
					"project_name": f"Perf {number}",
					"pms_enabled": 1,
					"tracker_identifier": f"PF{number}",
					"tracker_members": [
						{"user": MGR, "project_role": "Manager"},
						{"user": DEV, "project_role": "Developer"},
					],
				}
			).insert()
			projects.append(doc.name)
		stamp = now()
		rows = [
			(
				f"PERF-{n:05d}",
				stamp,
				stamp,
				"Administrator",
				"Administrator",
				0,
				f"Item {n}",
				projects[n % 50],
				"Task",
				"New",
				"Normal",
				n % 2,
				0,
			)
			for n in range(10000)
		]
		frappe.db.bulk_insert(
			"Work Item",
			[
				"name",
				"creation",
				"modified",
				"modified_by",
				"owner",
				"docstatus",
				"subject",
				"project",
				"tracker",
				"status",
				"priority",
				"is_closed",
				"idx",
			],
			rows,
			ignore_duplicates=True,
		)
		self.assertGreaterEqual(frappe.db.count("Work Item"), 10000)
		with self.as_user(DEV):
			started = time.perf_counter()
			page = frappe.get_list(
				"Work Item",
				filters={"is_closed": 0},
				fields=["name", "subject", "status", "priority", "assigned_to", "due_date"],
				order_by="modified desc",
				limit_page_length=20,
			)
			total = frappe.get_list(
				"Work Item", filters={"is_closed": 0}, fields=[{"COUNT": "*", "as": "n"}]
			)[0].n
			elapsed = time.perf_counter() - started
		self.assertEqual(len(page), 20)
		self.assertGreater(total, 0)
		self.assertLess(elapsed, 2, f"list took {elapsed:.2f}s")

	def test_save_with_ancestors_and_time_entries_under_one_second(self):
		"""Saving an item with 3 ancestors and 20 time entries takes under 1 second."""
		parent = None
		for _ in range(4):
			parent = self.new_item(MGR, tracker="Task", parent_work_item=parent.name if parent else None)
		for day in range(20):
			self.logged_time(DEV, parent.name, 0.5, date=frappe.utils.add_days(frappe.utils.today(), -day))
		parent.reload()
		with self.as_user(MGR):
			parent.subject = "Timed save"
			started = time.perf_counter()
			parent.save()
			elapsed = time.perf_counter() - started
		self.assertLess(elapsed, 1, f"save took {elapsed:.2f}s")
