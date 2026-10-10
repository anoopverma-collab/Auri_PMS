"""Time Entry rules (T-090 .. T-100)."""

import frappe
from frappe.utils import add_days, today

from auri_pms.tracking.tests.utils import DEV, MGR, REP, TM, TrackerTestCase, days_ago


class TestTimeEntry(TrackerTestCase):
	def setting(self, **values):
		settings = frappe.get_doc("PMS Settings")
		settings.update(values)
		settings.save()

	def test_t090_project_filled_from_item(self):
		"""T-090: an entry with a work item and no project gets the item's project."""
		item = self.new_item(MGR)
		entry = self.logged_time(DEV, item.name, 1)
		self.assertEqual(entry.project, self.ALP)

	def test_t091_project_must_match(self):
		"""T-091: work item ALP with project BET is rejected."""
		item = self.new_item(MGR)
		self.assertThrows(
			"Project must match the work item's project",
			lambda: self.logged_time(MGR, item.name, 1, project=self.BET),
		)

	def test_t092_reporter_cannot_log_time(self):
		"""T-092: rep has no can_log_time."""
		item = self.new_item(MGR)
		self.assertThrows(
			"You are not allowed to log time in Project", lambda: self.logged_time(REP, item.name, 1)
		)

	def test_t093_logging_for_others(self):
		"""T-093: dev cannot log for mgr; mgr can log for dev."""
		item = self.new_item(MGR)
		self.assertThrows(
			"You can only change your own time entries",
			lambda: self.logged_time(DEV, item.name, 1, entry_user=MGR),
		)
		self.assertEqual(self.logged_time(MGR, item.name, 1, entry_user=DEV).user, DEV)

	def test_t094_edit_and_delete_own_only(self):
		"""T-094: dev edits/deletes own entries; dev cannot edit mgr's."""
		item = self.new_item(MGR)
		own, theirs = self.logged_time(DEV, item.name, 1), self.logged_time(MGR, item.name, 1)
		self.save_as(DEV, own, hours=2)
		self.assertThrows(
			"You can only change your own time entries", lambda: self.save_as(DEV, theirs, hours=3)
		)
		with self.as_user(DEV):
			frappe.delete_doc("Time Entry", own.name)
			self.assertRaises(frappe.ValidationError, frappe.delete_doc, "Time Entry", theirs.name)

	def test_t095_hours_bounds(self):
		"""T-095: 0 and 25 hours are rejected."""
		item = self.new_item(MGR)
		self.assertThrows("Hours must be greater than 0", lambda: self.logged_time(DEV, item.name, 0))
		self.assertThrows("Hours per entry cannot exceed 24", lambda: self.logged_time(DEV, item.name, 25))

	def test_t096_daily_limit_across_projects(self):
		"""T-096: 8h on ALP plus 5h on BET exceeds the daily limit of 12."""
		self.logged_time(MGR, None, 8, project=self.ALP)
		self.assertThrows("would log 13.0 hours on", lambda: self.logged_time(MGR, None, 5, project=self.BET))

	def test_t097_future_date(self):
		"""T-097: tomorrow is rejected."""
		self.assertThrows(
			"Time cannot be logged for a future date",
			lambda: self.logged_time(DEV, None, 1, project=self.ALP, date=add_days(today(), 1)),
		)

	def test_t098_lock_days(self):
		"""T-098: with a 7 day lock dev cannot back-date 10 days; tm can."""
		self.setting(time_entry_lock_days=7)
		self.assertThrows(
			"Time entries older than 7 days are locked",
			lambda: self.logged_time(DEV, None, 1, project=self.ALP, date=days_ago(10)),
		)
		self.assertTrue(self.logged_time(TM, None, 1, project=self.ALP, date=days_ago(10)).name)

	def test_t099_closed_item(self):
		"""T-099: time on a closed item is rejected unless the setting allows it."""
		item = self.new_item(MGR, tracker="Task")
		self.save_as(MGR, item, status="Closed")
		self.assertThrows(
			f"Cannot log time on closed work item {item.name}", lambda: self.logged_time(DEV, item.name, 1)
		)
		self.setting(allow_time_on_closed_items=1)
		self.assertTrue(self.logged_time(DEV, item.name, 1).name)

	def test_t100_project_only_entry(self):
		"""T-100: an entry without a work item saves on the project."""
		entry = self.logged_time(DEV, None, 1, project=self.ALP)
		self.assertEqual((entry.work_item, entry.project), (None, self.ALP))
