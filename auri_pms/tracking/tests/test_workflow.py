"""Status workflow rules (T-040 .. T-051); the Bug workflow ships in install.BUG_WORKFLOW."""

import frappe

from auri_pms.tracking.api import get_allowed_statuses
from auri_pms.tracking.tests.utils import DEV, MGR, REP, TM, TrackerTestCase


class TestWorkflow(TrackerTestCase):
	def test_t040_dev_new_to_resolved(self):
		"""T-040: dev moves New -> In Progress -> Resolved."""
		item = self.new_item(DEV)
		self.save_as(DEV, item, status="In Progress")
		self.save_as(DEV, item, status="Resolved")
		self.assertEqual(frappe.db.get_value("Work Item", item.name, "status"), "Resolved")

	def test_t041_dev_cannot_close(self):
		"""T-041: dev cannot move Resolved -> Closed."""
		item = self.new_item(DEV, status=None)
		self.save_as(DEV, item, status="In Progress")
		self.save_as(DEV, item, status="Resolved")
		self.assertThrows(
			"Moving from Resolved to Closed is not allowed for your role on tracker Bug",
			lambda: self.save_as(DEV, item, status="Closed"),
		)

	def test_t042_reporter_closes_resolved(self):
		"""T-042: rep closes the resolved bug; closed_on/by set and done = 100."""
		item = self.new_item(REP)
		self.save_as(DEV, item, status="In Progress")
		self.save_as(DEV, item, status="Resolved")
		item.reload()
		self.save_as(REP, item, status="Closed")
		item.reload()
		self.assertEqual((item.status, item.closed_by, item.done_percent), ("Closed", REP, 100))
		self.assertTrue(item.closed_on)

	def test_t043_dev_cannot_reject(self):
		"""T-043: New -> Rejected is Manager only."""
		item = self.new_item(DEV)
		self.assertThrows("is not allowed for your role", lambda: self.save_as(DEV, item, status="Rejected"))

	def test_t044_manager_bypass(self):
		"""T-044: tm moves New -> Closed directly."""
		item = self.new_item(DEV)
		self.save_as(TM, item, status="Closed")
		self.assertEqual(frappe.db.get_value("Work Item", item.name, "status"), "Closed")

	def test_t045_task_tracker_any_move(self):
		"""T-045: the Task tracker has an empty table, so any move is allowed."""
		item = self.new_item(DEV, tracker="Task")
		for status in ("Closed", "New", "Rejected", "Feedback"):
			self.save_as(DEV, item, status=status)
			item.reload()

	def test_t046_allowed_statuses_for_dev(self):
		"""T-046: on a New Bug dev may only move to In Progress."""
		item = self.new_item(DEV)
		with self.as_user(DEV):
			self.assertEqual(get_allowed_statuses(item.name), ["In Progress"])
		with self.as_user(MGR):
			self.assertEqual(get_allowed_statuses(item.name), ["In Progress", "Rejected"])
		with self.as_user(TM):
			self.assertEqual(
				get_allowed_statuses(item.name), ["In Progress", "Feedback", "Resolved", "Closed", "Rejected"]
			)

	def test_t047_reopen_clears_closed_fields(self):
		"""T-047: mgr reopens a closed item; closed_on and closed_by are cleared."""
		item = self.new_item(DEV)
		self.save_as(TM, item, status="Closed")
		item.reload()
		self.assertTrue(item.closed_on)
		self.save_as(MGR, item, status="In Progress")
		item.reload()
		self.assertFalse(item.closed_on or item.closed_by)

	def test_t048_close_parent_with_open_child(self):
		"""T-048: a parent cannot close while a child is open; the message lists the child."""
		parent = self.new_item(MGR, tracker="Task")
		child = self.new_item(MGR, tracker="Task", parent_work_item=parent.name)
		self.assertThrows(
			f"Close all subtasks first: {child.name}", lambda: self.save_as(MGR, parent, status="Closed")
		)

	def test_t049_children_rule_can_be_disabled(self):
		"""T-049: with require_children_closed = 0 the parent closes."""
		settings = frappe.get_doc("Tracker Settings")
		settings.require_children_closed = 0
		settings.save()
		parent = self.new_item(MGR, tracker="Task")
		self.new_item(MGR, tracker="Task", parent_work_item=parent.name)
		self.save_as(MGR, parent, status="Closed")
		self.assertEqual(frappe.db.get_value("Work Item", parent.name, "status"), "Closed")

	def test_t050_blocked_item_cannot_close(self):
		"""T-050: an item blocked by an open item cannot close; it can once the blocker is closed."""
		blocker = self.new_item(MGR, tracker="Task")
		blocked = self.new_item(MGR, tracker="Task")
		blocked.append("relations", {"relation_type": "Blocked by", "related_work_item": blocker.name})
		self.save_as(MGR, blocked)
		blocked.reload()
		self.assertThrows(
			f"blocked by open items: {blocker.name}", lambda: self.save_as(MGR, blocked, status="Closed")
		)
		blocked.reload()
		blocker.reload()
		self.save_as(MGR, blocker, status="Closed")
		self.save_as(MGR, blocked, status="Closed")
		self.assertEqual(frappe.db.get_value("Work Item", blocked.name, "status"), "Closed")

	def test_t051_reopen_child_of_closed_parent(self):
		"""T-051: reopening a child leaves the closed parent alone and shows a message."""
		parent = self.new_item(MGR, tracker="Task")
		child = self.new_item(MGR, tracker="Task", parent_work_item=parent.name)
		self.save_as(MGR, child, status="Closed")
		self.save_as(MGR, parent, status="Closed")
		child.reload()
		frappe.local.message_log = []
		self.save_as(MGR, child, status="In Progress")
		self.assertEqual(frappe.db.get_value("Work Item", parent.name, "status"), "Closed")
		self.assertTrue(any("is closed" in str(m) for m in frappe.local.message_log))
