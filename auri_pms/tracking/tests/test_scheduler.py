"""Daily digest (T-124, T-125) and assignment / status notifications (T-126, T-127)."""

import frappe

from auri_pms.tracking.tasks import send_due_digests
from auri_pms.tracking.tests.utils import DEV, MGR, REP, TrackerTestCase, days_ago


class TestScheduler(TrackerTestCase):
	def emails_to(self, user, subject_part=None):
		parents = frappe.get_all("Email Queue Recipient", filters={"recipient": user}, pluck="parent")
		rows = frappe.get_all(
			"Email Queue", filters={"name": ["in", parents or [""]]}, fields=["name", "message"]
		)
		return [r for r in rows if not subject_part or subject_part in r.message]

	def test_t124_one_digest_per_assignee(self):
		"""T-124: dev gets one email listing 2 due-tomorrow and 1 overdue item; mgr gets none."""
		names = [
			self.new_item(MGR, assigned_to=DEV, due_date=due).name
			for due in (frappe.utils.add_days(frappe.utils.today(), 1),) * 2 + (days_ago(2),)
		]
		frappe.db.delete("Email Queue")
		send_due_digests()
		digests = self.emails_to(DEV, "Work items due")
		self.assertEqual(len(digests), 1)
		for name in names:
			self.assertIn(name, digests[0].message)
		self.assertFalse(self.emails_to(MGR, "Work items due"))

	def test_t125_closed_items_excluded(self):
		"""T-125: a closed overdue item is not included."""
		item = self.new_item(MGR, tracker="Task", assigned_to=DEV, due_date=days_ago(2))
		self.save_as(MGR, item, status="Closed")
		frappe.db.delete("Email Queue")
		send_due_digests()
		self.assertFalse(self.emails_to(DEV, "Work items due"))

	def test_t126_assignment_notification(self):
		"""T-126: assigning to dev notifies dev; assigning to yourself does not notify."""
		item = self.new_item(MGR, assigned_to=DEV)
		self.assertTrue(
			frappe.db.exists(
				"Notification Log", {"for_user": DEV, "type": "Assignment", "document_name": item.name}
			)
		)
		own = self.new_item(MGR, assigned_to=MGR)
		self.assertFalse(
			frappe.db.exists(
				"Notification Log", {"for_user": MGR, "type": "Assignment", "document_name": own.name}
			)
		)

	def test_t127_status_change_email(self):
		"""T-127: dev moving rep's item emails rep (author) and not dev."""
		item = self.new_item(REP)
		frappe.db.delete("Email Queue")
		self.save_as(DEV, item, status="In Progress")
		self.assertEqual(len(self.emails_to(REP, item.name)), 1)
		self.assertFalse(self.emails_to(DEV, item.name))

	def test_missing_outgoing_account_never_blocks_or_nags(self):
		"""Without an outgoing Email Account a status change still saves and shows no error popup."""
		item = self.new_item(REP)
		frappe.db.delete("Email Account", {"default_outgoing": 1})
		frappe.local.message_log = []
		self.save_as(DEV, item, status="In Progress")
		self.assertEqual(frappe.db.get_value("Work Item", item.name, "status"), "In Progress")
		self.assertFalse([m for m in frappe.local.message_log if "outgoing" in str(m).lower()])
