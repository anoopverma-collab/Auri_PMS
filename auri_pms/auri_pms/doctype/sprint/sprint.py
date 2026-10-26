"""Sprint - a time-boxed plan of work items within one project."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from auri_pms.auri_pms.utils import ensure_pms_project, has_capability, linked_tickets, recalc_sprint

STATUS_ORDER = {"Planned": 0, "Active": 1, "Completed": 2}


class Sprint(Document):
	"""Sprint with start/end dates, a lifecycle (Planned -> Active -> Completed) and roll-up progress."""

	def before_insert(self) -> None:
		"""The project identifier is part of the name, so fetch it before naming."""
		self.set_project_identifier()

	def validate(self) -> None:
		"""Capability, dates, overlap, lifecycle and carry-over rules."""
		self.old = self.get_doc_before_save()
		self.set_project_identifier()
		self.validate_can_manage()
		self.validate_dates()
		self.validate_overlap()
		self.validate_status()
		self.validate_completed_is_locked()
		self.validate_carry_over()

	def set_project_identifier(self) -> None:
		"""Copy the project identifier (needed for the document name)."""
		ensure_pms_project(self.project, _("creating sprints"))
		identifier = frappe.db.get_value("Project", self.project, "tracker_identifier")
		if not identifier:
			frappe.throw(_("Set an Identifier on Project {0} before creating sprints").format(self.project))
		self.project_identifier = identifier

	def validate_can_manage(self) -> None:
		"""Only users with can_manage_releases (or managers) create or edit sprints."""
		if not has_capability(self.project, "can_manage_releases"):
			frappe.throw(_("You are not allowed to manage sprints in Project {0}").format(self.project))

	def validate_dates(self) -> None:
		"""End Date cannot be before Start Date."""
		if getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("End Date cannot be before Start Date"))

	def validate_overlap(self) -> None:
		"""Sprints of one project may not overlap."""
		clash = frappe.db.sql(
			"""select name from `tabSprint`
			where project = %s and name != %s and start_date <= %s and end_date >= %s limit 1""",
			(self.project, self.name or "", self.end_date, self.start_date),
		)
		if clash:
			frappe.throw(_("Sprint {0} already covers these dates").format(clash[0][0]))

	def validate_status(self) -> None:
		"""Planned -> Active -> Completed only; one Active sprint per project."""
		previous = self.old.status if self.old else None
		if self.status == previous:
			return
		if self.status == "Completed" and previous != "Active":
			frappe.throw(_("Start the sprint before completing it"))
		if previous and STATUS_ORDER[self.status] < STATUS_ORDER[previous]:
			frappe.throw(_("A {0} sprint cannot move back to {1}").format(previous, self.status))
		if self.status == "Active":
			other = frappe.db.get_value(
				"Sprint",
				{"project": self.project, "status": "Active", "name": ("!=", self.name or "")},
				"name",
			)
			if other:
				frappe.throw(_("Sprint {0} is already active in Project {1}").format(other, self.project))

	def validate_completed_is_locked(self) -> None:
		"""Completed sprints keep their dates and goal."""
		if self.old and self.old.status == "Completed":
			for fieldname in ("start_date", "end_date", "goal", "sprint_name"):
				if str(self.get(fieldname) or "") != str(self.old.get(fieldname) or ""):
					frappe.throw(_("Completed sprints cannot be changed"))

	def validate_carry_over(self) -> None:
		"""The sprint receiving unfinished items must be another open sprint of the same project."""
		if not self.carry_over_to:
			return
		project, status = frappe.db.get_value("Sprint", self.carry_over_to, ["project", "status"])
		if self.carry_over_to == self.name or project != self.project or status == "Completed":
			frappe.throw(
				_("{0} must be another Planned or Active sprint of Project {1}").format(
					self.carry_over_to, self.project
				)
			)

	def on_update(self) -> None:
		"""Completing a sprint moves unfinished items to the next sprint or back to the backlog."""
		if self.status == "Completed" and self.old and self.old.status != "Completed":
			self.carry_over_open_items()
		recalc_sprint(self.name)

	def carry_over_open_items(self) -> None:
		"""Move every open item of this sprint to ``carry_over_to`` (or the backlog when blank)."""
		open_items = frappe.get_all(
			"Work Item", filters={"sprint": self.name, "is_closed": 0}, pluck="name", order_by="name asc"
		)
		for name in open_items:
			item = frappe.get_doc("Work Item", name)
			item.sprint = self.carry_over_to or None
			item.flags.ignore_tracker_rules = True  # a sprint manager closes the sprint, not the item owner
			item.save(ignore_permissions=True)
		recalc_sprint(self.carry_over_to)
		if open_items:
			frappe.msgprint(
				_("{0} unfinished items moved to {1}").format(
					len(open_items), self.carry_over_to or _("the backlog")
				),
				indicator="blue",
				alert=True,
			)

	def on_trash(self) -> None:
		"""Deleting needs the same capability; a sprint with items is refused by Frappe's link check."""
		self.validate_can_manage()


@frappe.whitelist()
def get_sprint_tickets(sprint: str) -> dict:
	"""The tickets allocated to a sprint: a count per status and per person, plus the tickets themselves."""
	frappe.has_permission("Sprint", "read", doc=sprint, throw=True)
	return linked_tickets("sprint", sprint)
