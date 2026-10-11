"""Work Item core rules (T-020 .. T-038)."""

import frappe

from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, REP, TM, TrackerTestCase


class TestWorkItem(TrackerTestCase):
	def test_t020_dev_creates_bug(self):
		"""T-020: name ALP-00001, author dev, status New, priority Normal."""
		item = self.new_item(DEV)
		self.assertEqual(item.name, "ALP-00001")
		self.assertEqual((item.author, item.status, item.priority), (DEV, "New", "Normal"))

	def test_t021_independent_series(self):
		"""T-021: ALP-00002, BET-00001, ALP-00003 (independent series per project)."""
		names = [
			self.new_item(DEV).name,
			self.new_item(MGR, self.BET).name,
			self.new_item(DEV).name,
		]
		self.assertEqual(names, ["ALP-00001", "BET-00001", "ALP-00002"])

	def test_t022_project_without_identifier(self):
		"""T-022: creating on Gamma is rejected with the identifier message."""
		self.assertThrows("Enable Auri PMS on Project", lambda: self.new_item(DEV, self.GAM))

	def test_t023_outsider_cannot_create_on_private(self):
		"""T-023: out cannot create on ALP."""
		self.assertThrows("You are not allowed to create work items in Project", lambda: self.new_item(OUT))

	def test_t024_outsider_can_create_on_public(self):
		"""T-024: out can create on BET through the public Reporter role."""
		self.assertTrue(self.new_item(OUT, self.BET).name.startswith("BET-"))

	def test_t025_tracker_not_enabled(self):
		"""T-025: Feature is not enabled on BET."""
		self.assertThrows(
			"is not enabled on Project", lambda: self.new_item(MGR, self.BET, tracker="Feature")
		)

	def test_t026_cannot_start_closed(self):
		"""T-026: insert with status Closed is rejected."""
		self.assertThrows("cannot start in a closed status", lambda: self.new_item(DEV, status="Closed"))

	def test_t027_project_is_set_only_once(self):
		"""T-027: project cannot change after insert."""
		item = self.new_item(MGR)
		item.project = self.BET
		self.assertThrows("Value cannot be changed", item.save)

	def test_t028_due_before_start(self):
		"""T-028: due_date before start_date is rejected."""
		self.assertThrows(
			"Due Date cannot be before Start Date",
			lambda: self.new_item(DEV, start_date="2026-10-10", due_date="2026-10-01"),
		)

	def test_t029_negative_estimate_and_percent(self):
		"""T-029: estimated_hours -1 and done_percent 120 are each rejected."""
		self.assertThrows(
			"Estimated Hours cannot be negative", lambda: self.new_item(DEV, estimated_hours=-1)
		)
		self.assertThrows("% Done must be between 0 and 100", lambda: self.new_item(DEV, done_percent=120))

	def test_t030_invalid_assignees(self):
		"""T-030: reporter (no can_be_assigned) and a non-member are rejected."""
		self.assertThrows("cannot be assigned work items", lambda: self.new_item(DEV, assigned_to=REP))
		self.assertThrows("cannot be assigned work items", lambda: self.new_item(DEV, assigned_to=OUT))

	def test_t031_assign_to_dev(self):
		"""T-031: assigning to dev creates an open ToDo and dev follows the item."""
		item = self.new_item(MGR, assigned_to=DEV)
		self.assertTrue(
			frappe.db.exists(
				"ToDo",
				{
					"reference_type": "Work Item",
					"reference_name": item.name,
					"allocated_to": DEV,
					"status": "Open",
				},
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"Document Follow", {"ref_doctype": "Work Item", "ref_docname": item.name, "user": DEV}
			)
		)

	def test_t032_reassign_closes_old_todo(self):
		"""T-032: reassigning dev -> mgr closes dev's ToDo and opens mgr's."""
		item = self.new_item(MGR, assigned_to=DEV)
		self.save_as(MGR, item, assigned_to=MGR)

		def status(user):
			return frappe.db.get_value(
				"ToDo",
				{"reference_type": "Work Item", "reference_name": item.name, "allocated_to": user},
				"status",
			)

		self.assertEqual((status(DEV), status(MGR)), ("Closed", "Open"))

	def test_t033_category_or_release_from_other_project(self):
		"""T-033: a BET category or release on an ALP item is rejected."""
		category = frappe.get_doc(
			{"doctype": "Work Item Category", "category_name": "UI", "project": self.BET}
		).insert()
		self.assertThrows("does not belong to Project", lambda: self.new_item(MGR, category=category.name))
		release = frappe.get_doc({"doctype": "Release", "release_name": "b1", "project": self.BET}).insert()
		self.assertThrows("does not belong to Project", lambda: self.new_item(MGR, release=release.name))

	def test_t034_locked_release(self):
		"""T-034: a new item in a Locked release is rejected; an existing one saves again."""
		locked = self.world.releases["v0"]
		self.assertThrows("only Open releases accept work items", lambda: self.new_item(MGR, release=locked))
		item = self.new_item(MGR, release=self.world.releases["v1"])
		frappe.db.set_value("Work Item", item.name, "release", locked, update_modified=False)
		item.reload()
		self.save_as(MGR, item, subject="Changed")  # unchanged release stays allowed
		self.assertEqual(item.release, locked)

	def test_t035_parent_rules(self):
		"""T-035: parent from another project, itself or its own grandchild is rejected."""
		other = self.new_item(MGR, self.BET)
		self.assertThrows(
			"Parent must be in the same project", lambda: self.new_item(MGR, parent_work_item=other.name)
		)
		root = self.new_item(MGR)
		child = self.new_item(MGR, parent_work_item=root.name)
		grandchild = self.new_item(MGR, parent_work_item=child.name)
		for target in (root.name, grandchild.name):
			root.reload()
			self.assertThrows(
				"its own parent or ancestor",
				lambda target=target: self.save_as(MGR, root, parent_work_item=target),
			)

	def test_t036_depth_limit(self):
		"""T-036: a chain of six levels with limit 5 rejects the sixth."""
		parent = None
		for _level in range(5):
			parent = self.new_item(MGR, parent_work_item=parent).name
		self.assertThrows("Maximum subtask depth of 5", lambda: self.new_item(MGR, parent_work_item=parent))

	def test_t037_reporter_edits_only_own(self):
		"""T-037: rep edits own item but not dev's."""
		own = self.new_item(REP)
		self.save_as(REP, own, subject="mine")
		theirs = self.new_item(DEV)
		self.assertThrows(
			"You can only edit work items you created or are assigned to",
			lambda: self.save_as(REP, theirs, subject="no"),
		)

	def test_t038_developer_edits_any(self):
		"""T-038: dev edits mgr's item (can_edit_any_item)."""
		item = self.new_item(MGR)
		self.save_as(DEV, item, subject="by dev")
		self.assertEqual(frappe.db.get_value("Work Item", item.name, "subject"), "by dev")
