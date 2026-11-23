"""Keep the Auri PMS data across an uninstall and install (auri_pms.data_keep)."""

from unittest.mock import patch

import frappe

from auri_pms.auri_pms.tests.utils import TrackerTestCase
from auri_pms.data_keep import TABLE, KeptData, keep_data_enabled


class TestDataKeep(TrackerTestCase):
	@classmethod
	def setUpClass(cls):
		# Creating a table commits. Do it before the test world is built, so only the empty table is committed.
		KeptData().ensure_table()
		frappe.db.commit()
		cls.addClassCleanup(frappe.db.sql_ddl, f"drop table if exists `{TABLE}`")
		super().setUpClass()

	def new_activity(self, name: str = "Kept Test"):
		return frappe.get_doc({"doctype": "PMS Activity Type", "activity_type": name}).insert()

	def test_a_deleted_record_comes_back_with_its_owner_and_dates(self):
		activity = self.new_activity()
		KeptData().save()
		frappe.db.delete("PMS Activity Type", activity.name)
		self.assertGreaterEqual(KeptData().restore_documents(), 1)
		back = frappe.get_doc("PMS Activity Type", activity.name)
		self.assertEqual((back.owner, str(back.creation)), (activity.owner, str(activity.creation)))

	def test_a_second_restore_creates_nothing(self):
		self.new_activity()
		KeptData().save()
		KeptData().restore_documents()
		self.assertEqual(KeptData().restore_documents(), 0)

	def test_an_existing_record_is_never_changed(self):
		activity = self.new_activity()
		KeptData().save()
		frappe.db.set_value("PMS Activity Type", activity.name, "is_active", 0)
		KeptData().restore_documents()
		self.assertEqual(frappe.db.get_value("PMS Activity Type", activity.name, "is_active"), 0)

	def test_a_single_keeps_only_what_was_stored(self):
		frappe.db.delete("Singles", {"doctype": "PMS Settings", "field": "max_hours_per_day"})
		KeptData().save()
		row = frappe.db.sql(
			"select data from `__auri_pms_kept` where kind = 'single' and doctype = 'PMS Settings'"
		)
		self.assertNotIn("max_hours_per_day", row[0][0])

	def test_a_missing_single_value_is_restored(self):
		frappe.db.set_single_value("PMS Settings", "max_hours_per_day", 7)
		KeptData().save()
		frappe.db.delete("Singles", {"doctype": "PMS Settings", "field": "max_hours_per_day"})
		KeptData().restore_documents()
		self.assertEqual(frappe.db.get_single_value("PMS Settings", "max_hours_per_day"), 7)

	def test_the_naming_counter_is_lifted(self):
		self.new_activity("ZZK-00001")
		frappe.db.sql("delete from `tabSeries` where name = 'ZZK-'")
		frappe.db.sql("insert into `tabSeries` (name, current) values ('ZZK-', 5)")
		KeptData().save()
		frappe.db.sql("update `tabSeries` set current = 1 where name = 'ZZK-'")
		KeptData().restore_documents()
		self.assertEqual(frappe.db.sql("select current from `tabSeries` where name = 'ZZK-'")[0][0], 5)

	def test_project_fields_and_members_come_back(self):
		members = frappe.db.count("Project Member", {"parent": self.ALP, "parenttype": "Project"})
		self.assertGreater(members, 0)
		frappe.db.set_value("Project", self.ALP, "pms_budget_hours", 123)
		KeptData().save()
		frappe.db.set_value("Project", self.ALP, "pms_budget_hours", 0)
		frappe.db.delete("Project Member", {"parent": self.ALP, "parenttype": "Project"})
		KeptData().restore_projects(sync=False)
		self.assertEqual(frappe.db.get_value("Project", self.ALP, "pms_budget_hours"), 123)
		self.assertEqual(
			frappe.db.count("Project Member", {"parent": self.ALP, "parenttype": "Project"}), members
		)

	def test_a_clean_uninstall_can_be_chosen(self):
		self.assertTrue(keep_data_enabled())
		with patch.dict(frappe.conf, {"auri_pms_drop_data_on_uninstall": 1}):
			self.assertFalse(keep_data_enabled())
