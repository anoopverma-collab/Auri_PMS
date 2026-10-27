"""Work Item core rules (T-020 .. T-038)."""

import frappe

from auri_pms.auri_pms.project_hooks import apply_custom_values
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

	def test_t024_outsider_cannot_create_on_public(self):
		"""T-024: out is not allocated to the public project BET, so cannot create there."""
		with self.assertRaises(frappe.ValidationError):
			self.new_item(OUT, self.BET)

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

	def test_actual_end_before_actual_start(self):
		"""The actual end date cannot come before the actual start date."""
		self.assertThrows(
			"Actual End Date cannot be before Actual Start Date",
			lambda: self.new_item(DEV, actual_start_date="2026-10-10", actual_end_date="2026-10-01"),
		)
		item = self.new_item(DEV, actual_start_date="2026-10-01", actual_end_date="2026-10-05")
		self.assertEqual(str(item.actual_end_date), "2026-10-05")

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

	# ---- Closed On: PMS Settings > Keep Closed On Visible and Editable ------------------------------
	def close_with_date(self, date: str):
		item = self.new_item(MGR, tracker="Task")
		self.save_as(MGR, item, status="Closed", closed_on=date)
		return frappe.get_doc("Work Item", item.name)

	def test_closed_on_entered_date_is_kept_when_setting_is_on(self):
		"""With the switch on, a Closed On typed while closing a ticket is kept."""
		frappe.db.set_single_value("PMS Settings", "keep_closed_on_editable", 1)
		item = self.close_with_date("2026-10-01 10:30:00")
		self.assertEqual(str(item.closed_on), "2026-10-01 10:30:00")
		self.assertEqual(item.closed_by, MGR)

	def test_closed_on_is_stamped_when_setting_is_off(self):
		"""With the switch off (the default) the closing time is set whatever was typed."""
		frappe.db.set_single_value("PMS Settings", "keep_closed_on_editable", 0)
		item = self.close_with_date("2026-10-01 10:30:00")
		self.assertNotEqual(str(item.closed_on), "2026-10-01 10:30:00")
		self.assertTrue(item.closed_on)

	def test_closed_on_is_stamped_when_none_is_entered(self):
		"""With the switch on and no date typed, the closing time is still set."""
		frappe.db.set_single_value("PMS Settings", "keep_closed_on_editable", 1)
		item = self.new_item(MGR, tracker="Task")
		self.save_as(MGR, item, status="Closed")
		self.assertTrue(frappe.db.get_value("Work Item", item.name, "closed_on"))

	def test_reopening_clears_closed_on(self):
		"""A ticket that is opened again loses Closed On and Closed By, with the switch on too."""
		frappe.db.set_single_value("PMS Settings", "keep_closed_on_editable", 1)
		item = self.close_with_date("2026-10-01 10:30:00")
		self.save_as(MGR, item, status="New")
		self.assertEqual(
			frappe.db.get_value("Work Item", item.name, ["closed_on", "closed_by"]), (None, None)
		)

	# ---- Project custom fields (Project > Custom Fields) copied to the tickets -----------------------
	def set_project_custom(self, count, **values):
		frappe.db.set_value("Project", self.ALP, {"pms_custom_count": str(count), **values})

	def custom_of(self, item):
		fields = ["project_custom_count", *(f"project_custom_{n}" for n in range(1, 6))]
		return dict(zip(fields, frappe.db.get_value("Work Item", item.name, fields), strict=True))

	def test_ticket_starts_with_the_projects_custom_values(self):
		"""A new ticket gets the project's count and the values up to that count, and nothing beyond it."""
		self.set_project_custom(3, pms_custom_1="Alpha", pms_custom_2="Beta", pms_custom_4="Hidden")
		got = self.custom_of(self.new_item(MGR))
		self.assertEqual(got["project_custom_count"], 3)
		self.assertEqual((got["project_custom_1"], got["project_custom_2"]), ("Alpha", "Beta"))
		self.assertIsNone(got["project_custom_4"])

	def test_value_typed_on_a_ticket_is_kept(self):
		"""The fields are editable on the ticket, and saving again does not put the project's value back."""
		self.set_project_custom(3, pms_custom_1="Alpha")
		item = self.new_item(MGR)
		self.save_as(MGR, item, project_custom_1="Mine", project_custom_2="Typed")
		self.save_as(MGR, item, subject="saved again")
		got = self.custom_of(item)
		self.assertEqual((got["project_custom_1"], got["project_custom_2"]), ("Mine", "Typed"))

	def test_project_change_follows_unless_the_ticket_has_its_own(self):
		"""A changed project value reaches a ticket that held the old one; a value typed on the ticket stays."""
		self.set_project_custom(5, pms_custom_1="Alpha", pms_custom_5="Old5")
		item = self.new_item(MGR)
		self.save_as(MGR, item, project_custom_5="Mine")
		old = frappe.db.get_value(
			"Project",
			self.ALP,
			["pms_custom_count", *(f"pms_custom_{n}" for n in range(1, 11))],
			as_dict=True,
		)
		self.set_project_custom(5, pms_custom_1="Alpha2", pms_custom_5="New5")
		apply_custom_values(self.ALP, dict(old))
		got = self.custom_of(item)
		self.assertEqual((got["project_custom_1"], got["project_custom_5"]), ("Alpha2", "Mine"))

	def test_lowering_the_count_clears_the_extra_values(self):
		"""Custom fields beyond the project's new number are emptied on its tickets."""
		self.set_project_custom(5, pms_custom_1="Alpha", pms_custom_4="Four")
		item = self.new_item(MGR)
		self.assertEqual(self.custom_of(item)["project_custom_4"], "Four")
		old = frappe.db.get_value(
			"Project",
			self.ALP,
			["pms_custom_count", *(f"pms_custom_{n}" for n in range(1, 11))],
			as_dict=True,
		)
		self.set_project_custom(2)
		apply_custom_values(self.ALP, dict(old))
		got = self.custom_of(item)
		self.assertEqual((got["project_custom_count"], got["project_custom_1"]), (2, "Alpha"))
		self.assertIsNone(got["project_custom_4"])

	def test_project_without_custom_fields_leaves_tickets_empty(self):
		"""Count 0 (or unset): the ticket carries no custom values."""
		got = self.custom_of(self.new_item(MGR))
		self.assertFalse(got["project_custom_count"])
		self.assertIsNone(got["project_custom_1"])

	# ---- Additional Assignees ----------------------------------------------------------------------
	def open_todos(self, item, user):
		return frappe.get_all(
			"ToDo",
			filters={
				"reference_type": "Work Item",
				"reference_name": item.name,
				"allocated_to": user,
				"status": "Open",
			},
		)

	def test_additional_assignee_gets_a_todo(self):
		"""Each person in Additional Assignees gets the ticket in their ToDo list."""
		item = self.new_item(MGR, assigned_to=MGR)
		self.save_as(MGR, item, additional_assignees=[{"user": DEV}])
		self.assertEqual(len(self.open_todos(item, DEV)), 1)
		self.assertEqual(len(self.open_todos(item, MGR)), 1)

	def test_removing_an_additional_assignee_closes_the_todo(self):
		item = self.new_item(MGR, assigned_to=MGR)
		self.save_as(MGR, item, additional_assignees=[{"user": DEV}])
		item.reload()
		self.save_as(MGR, item, additional_assignees=[])
		self.assertFalse(self.open_todos(item, DEV))

	def test_additional_assignee_must_be_assignable_in_the_project(self):
		"""Same rule as Assigned To (R-11): someone outside the project is refused."""
		item = self.new_item(MGR)
		self.assertThrows(
			"cannot be assigned work items",
			lambda: self.save_as(MGR, item, additional_assignees=[{"user": OUT}]),
		)

	def test_duplicates_and_the_main_assignee_are_dropped(self):
		"""A person listed twice, or already the Assigned To, is kept once / not at all."""
		item = self.new_item(MGR, assigned_to=MGR)
		self.save_as(MGR, item, additional_assignees=[{"user": DEV}, {"user": DEV}, {"user": MGR}])
		item.reload()
		self.assertEqual([r.user for r in item.additional_assignees], [DEV])

	def test_my_work_lists_tickets_where_i_am_an_additional_assignee(self):
		"""My Work shows the ticket to the additional assignee as well as the main one."""
		from auri_pms.auri_pms.dashboards import get_my_work_data

		item = self.new_item(MGR, assigned_to=MGR)
		self.save_as(MGR, item, additional_assignees=[{"user": DEV}])
		data = get_my_work_data(DEV)
		names = {row.name for rows in data.groups.values() for row in rows}
		self.assertIn(item.name, names)

	def test_adding_assignees_does_not_change_assigned_to(self):
		"""Frappe's Assign To would make the last person the Assigned To; the real one must stay."""
		item = self.new_item(MGR, assigned_to=MGR)
		self.save_as(MGR, item, additional_assignees=[{"user": DEV}])
		self.assertEqual(frappe.db.get_value("Work Item", item.name, "assigned_to"), MGR)
		item.reload()
		self.save_as(MGR, item, additional_assignees=[])
		self.assertEqual(frappe.db.get_value("Work Item", item.name, "assigned_to"), MGR)

	# ---- Sprint on a closed ticket: PMS Settings > Allow Completed Sprint for Closed Tickets -----------
	def completed_sprint(self):
		sprint = frappe.get_doc(
			{
				"doctype": "Sprint",
				"sprint_name": "Done sprint",
				"project": self.ALP,
				"start_date": "2026-01-01",
				"end_date": "2026-01-14",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Sprint", sprint.name, "status", "Completed")
		return sprint

	def test_closed_ticket_cannot_move_to_a_completed_sprint_by_default(self):
		sprint = self.completed_sprint()
		item = self.closed_ticket()
		self.assertThrows(
			"only Planned or Active sprints", lambda: self.save_as(MGR, item, sprint=sprint.name)
		)

	def test_closed_ticket_can_move_to_a_completed_sprint_when_allowed(self):
		frappe.db.set_single_value("PMS Settings", "allow_completed_sprint_for_closed", 1)
		sprint = self.completed_sprint()
		item = self.closed_ticket()
		self.save_as(MGR, item, sprint=sprint.name)
		self.assertEqual(frappe.db.get_value("Work Item", item.name, "sprint"), sprint.name)

	def test_open_ticket_still_refuses_a_completed_sprint_when_allowed(self):
		frappe.db.set_single_value("PMS Settings", "allow_completed_sprint_for_closed", 1)
		sprint = self.completed_sprint()
		item = self.new_item(MGR, tracker="Task")
		self.assertThrows(
			"only Planned or Active sprints", lambda: self.save_as(MGR, item, sprint=sprint.name)
		)

	def closed_ticket(self):
		item = self.new_item(MGR, tracker="Task")
		self.save_as(MGR, item, status="Closed")
		return item
