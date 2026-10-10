"""Hour and progress roll-ups (T-070 .. T-076)."""

import frappe

from auri_pms.tracking.tests.utils import DEV, MGR, TrackerTestCase


class TestRollups(TrackerTestCase):
	def values(self, item, *fields):
		return frappe.db.get_value("Work Item", item.name, list(fields), as_dict=True)

	def test_t070_child_spent_hours(self):
		"""T-070: 2h + 3h on child C gives spent 5."""
		child = self.new_item(MGR)
		self.logged_time(DEV, child.name, 2)
		self.logged_time(DEV, child.name, 3)
		self.assertEqual(self.values(child, "spent_hours").spent_hours, 5)

	def test_t071_parent_totals(self):
		"""T-071: P (est 4, 1h) + C (est 6, 5h) -> total spent 6, total estimated 10."""
		parent = self.new_item(MGR, estimated_hours=4)
		child = self.new_item(MGR, estimated_hours=6, parent_work_item=parent.name)
		self.logged_time(DEV, parent.name, 1)
		self.logged_time(DEV, child.name, 5)
		self.assertEqual(
			self.values(parent, "total_spent_hours", "total_estimated_hours"),
			{"total_spent_hours": 6, "total_estimated_hours": 10},
		)

	def test_t072_move_and_delete_entries(self):
		"""T-072: moving an entry to P and deleting one keep every total correct."""
		parent = self.new_item(MGR, estimated_hours=4)
		child = self.new_item(MGR, parent_work_item=parent.name)
		first = self.logged_time(DEV, child.name, 2)
		second = self.logged_time(DEV, child.name, 3)
		self.save_as(DEV, first, work_item=parent.name)
		self.assertEqual(
			self.values(child, "spent_hours", "total_spent_hours"), {"spent_hours": 3, "total_spent_hours": 3}
		)
		self.assertEqual(
			self.values(parent, "spent_hours", "total_spent_hours"),
			{"spent_hours": 2, "total_spent_hours": 5},
		)
		with self.as_user(DEV):
			frappe.delete_doc("Time Entry", second.name)
		self.assertEqual(self.values(child, "total_spent_hours").total_spent_hours, 0)
		self.assertEqual(self.values(parent, "total_spent_hours").total_spent_hours, 2)

	def test_t073_reparent(self):
		"""T-073: moving C from P to Q updates both chains."""
		p, q = self.new_item(MGR, estimated_hours=1), self.new_item(MGR, estimated_hours=2)
		child = self.new_item(MGR, estimated_hours=5, parent_work_item=p.name)
		self.logged_time(DEV, child.name, 4)
		self.assertEqual(
			self.values(p, "total_estimated_hours", "total_spent_hours"),
			{"total_estimated_hours": 6, "total_spent_hours": 4},
		)
		child.reload()
		self.save_as(MGR, child, parent_work_item=q.name)
		self.assertEqual(
			self.values(p, "total_estimated_hours", "total_spent_hours"),
			{"total_estimated_hours": 1, "total_spent_hours": 0},
		)
		self.assertEqual(
			self.values(q, "total_estimated_hours", "total_spent_hours"),
			{"total_estimated_hours": 7, "total_spent_hours": 4},
		)

	def test_t074_weighted_progress(self):
		"""T-074: C1 (est 2, 50%) and C2 (est 6, closed) -> P done 87.5, not editable."""
		parent = self.new_item(MGR, tracker="Task")
		self.new_item(MGR, tracker="Task", estimated_hours=2, done_percent=50, parent_work_item=parent.name)
		c2 = self.new_item(MGR, tracker="Task", estimated_hours=6, parent_work_item=parent.name)
		self.save_as(MGR, c2, status="Closed")
		self.assertEqual(self.values(parent, "done_percent").done_percent, 87.5)
		parent.reload()
		self.save_as(MGR, parent, done_percent=10)
		self.assertEqual(self.values(parent, "done_percent").done_percent, 87.5)

	def test_t075_simple_average(self):
		"""T-075: one child without an estimate switches to a simple average (75)."""
		parent = self.new_item(MGR, tracker="Task")
		self.new_item(MGR, tracker="Task", estimated_hours=2, done_percent=50, parent_work_item=parent.name)
		c2 = self.new_item(MGR, tracker="Task", parent_work_item=parent.name)
		self.save_as(MGR, c2, status="Closed")
		self.assertEqual(self.values(parent, "done_percent").done_percent, 75)

	def test_t076_rollups_leave_history_alone(self):
		"""T-076: roll-ups add no Version rows and do not touch modified."""
		parent = self.new_item(MGR)
		child = self.new_item(MGR, parent_work_item=parent.name)
		self.save_as(MGR, parent, subject="touch")  # one real Version row exists for the parent
		self.assertEqual(frappe.db.count("Version", {"docname": parent.name}), 1)
		before = (
			frappe.db.count("Version", {"docname": parent.name}),
			self.values(parent, "modified").modified,
		)
		self.logged_time(DEV, child.name, 2)
		after = (
			frappe.db.count("Version", {"docname": parent.name}),
			self.values(parent, "modified").modified,
		)
		self.assertEqual(before, after)
		self.assertEqual(self.values(parent, "total_spent_hours").total_spent_hours, 2)
