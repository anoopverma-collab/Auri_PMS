"""End-to-end script of UAT-01 .. UAT-08 (spec section 9), run as the named users of the fixture world."""

import frappe

from auri_pms.auri_pms.api import get_allowed_statuses, log_time
from auri_pms.auri_pms.tests.utils import DEV, MGR, REP, TM, TrackerTestCase


class TestEndToEnd(TrackerTestCase):
	def create(self, user, doctype, **values):
		with self.as_user(user):
			return frappe.get_doc({"doctype": doctype, **values}).insert()

	def move(self, user, name, status):
		with self.as_user(user):
			doc = frappe.get_doc("Work Item", name)
			doc.status = status
			doc.save(ignore_version=False)
		return frappe.get_doc("Work Item", name)

	def emails_to(self, user):
		parents = frappe.get_all("Email Queue Recipient", filters={"recipient": user}, pluck="parent")
		return frappe.get_all(
			"Email Queue", filters={"name": ["in", parents or [""]]}, fields=["name", "message"]
		)

	def test_uat_01_to_08(self):
		"""UAT-01 .. UAT-08 in order."""
		# UAT-01 set up a project (WEB, or WEBT when a real project already uses WEB)
		ident = "WEB" if not frappe.db.exists("Project", {"tracker_identifier": "WEB"}) else "WEBT"
		project = self.create(
			TM,
			"Project",
			project_name="Website Revamp",
			pms_enabled=1,
			tracker_identifier=ident,
			tracker_members=[
				{"user": MGR, "project_role": "Manager"},
				{"user": DEV, "project_role": "Developer"},
				{"user": REP, "project_role": "Reporter"},
			],
			enabled_trackers=[{"tracker": "Bug"}, {"tracker": "Task"}],
		).name
		v1 = self.create(MGR, "Release", release_name="v1", project=project).name  # named <ident>-v1
		self.create(MGR, "Release", release_name="v2", project=project)
		category = self.create(MGR, "Work Item Category", category_name="UI", project=project).name
		self.assertIn("Auri PMS User", frappe.get_roles(REP))

		# UAT-02 report a bug
		bug = self.create(
			REP,
			"Work Item",
			subject="Login button misaligned",
			project=project,
			tracker="Bug",
			priority="High",
		)
		self.assertEqual((bug.name, bug.status, bug.author), (f"{ident}-00001", "New", REP))
		with self.as_user(REP):
			self.assertIn(bug.name, frappe.get_list("Work Item", pluck="name"))

		# UAT-03 triage and assign
		with self.as_user(MGR):
			doc = frappe.get_doc("Work Item", bug.name)
			doc.update({"category": category, "release": v1, "assigned_to": DEV})
			doc.save()
		self.assertTrue(
			frappe.db.exists("ToDo", {"reference_name": bug.name, "allocated_to": DEV, "status": "Open"})
		)
		self.assertTrue(
			frappe.db.exists(
				"Notification Log", {"for_user": DEV, "type": "Assignment", "document_name": bug.name}
			)
		)
		for user in (DEV, REP):
			self.assertTrue(
				frappe.db.exists("Document Follow", {"ref_docname": bug.name, "user": user}), user
			)

		# UAT-04 work the bug
		with self.as_user(DEV):
			self.assertEqual(get_allowed_statuses(bug.name), ["In Progress"])
		self.move(DEV, bug.name, "In Progress")
		with self.as_user(DEV):
			log_time(bug.name, 2, "Development")
		self.assertEqual(
			frappe.db.get_value("Work Item", bug.name, ["status", "spent_hours"], as_dict=True),
			{"status": "In Progress", "spent_hours": 2},
		)
		versions = frappe.get_all(
			"Version", filters={"ref_doctype": "Work Item", "docname": bug.name}, pluck="data"
		)
		self.assertTrue(any("In Progress" in v for v in versions))

		# UAT-05 resolve and verify
		with self.as_user(DEV):
			offered = get_allowed_statuses(bug.name)
		self.assertIn("Resolved", offered)
		self.assertNotIn("Closed", offered)
		frappe.db.delete("Email Queue")
		self.move(DEV, bug.name, "Resolved")
		self.assertTrue([e for e in self.emails_to(REP) if bug.name in e.message])
		closed = self.move(REP, bug.name, "Closed")
		self.assertEqual((closed.closed_by, closed.done_percent), (REP, 100))
		self.assertTrue(closed.closed_on)
		self.assertEqual(frappe.db.get_value("Release", v1, "percent_complete"), 100)

		# UAT-06 wrong transition
		other = self.create(REP, "Work Item", subject="Another", project=project, tracker="Bug")
		self.move(DEV, other.name, "In Progress")
		self.move(DEV, other.name, "Resolved")
		with self.assertRaises(frappe.ValidationError) as cm:
			self.move(DEV, other.name, "Closed")
		self.assertIn(
			"Moving from Resolved to Closed is not allowed for your role on tracker Bug", str(cm.exception)
		)

		# UAT-07 plan a feature with subtasks
		parent = self.create(
			MGR, "Work Item", subject="New checkout", project=project, tracker="Task", estimated_hours=0
		)
		first = self.create(
			MGR,
			"Work Item",
			subject="Cart",
			project=project,
			tracker="Task",
			estimated_hours=4,
			parent_work_item=parent.name,
		)
		self.create(
			MGR,
			"Work Item",
			subject="Payment",
			project=project,
			tracker="Task",
			estimated_hours=6,
			parent_work_item=parent.name,
		)
		with self.as_user(DEV):
			log_time(first.name, 3, "Development")
		self.assertEqual(
			frappe.db.get_value(
				"Work Item", parent.name, ["total_estimated_hours", "total_spent_hours"], as_dict=True
			),
			{"total_estimated_hours": 10, "total_spent_hours": 3},
		)

		# UAT-08 close a parent too early
		with self.assertRaises(frappe.ValidationError) as cm:
			self.move(MGR, parent.name, "Closed")
		self.assertIn("Close all subtasks first", str(cm.exception))
		self.assertIn(first.name, str(cm.exception))
