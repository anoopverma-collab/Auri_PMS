"""Work Item Status master (spec 3.2)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class WorkItemStatus(Document):
	"""A status a Work Item can be in; ``is_closed`` drives all open/closed logic."""

	def validate(self) -> None:
		"""Validate percent range and keep at least one open and one closed active status."""
		if self.default_done_percent not in (None, "") and not 0 <= cint(self.default_done_percent) <= 100:
			frappe.throw(_("% Done must be between 0 and 100"))
		if not self.is_new():
			self.validate_open_and_closed_exist(exclude_self=False)

	def after_insert(self) -> None:
		"""Add a Kanban column for the new status."""
		from auri_pms.install import add_status_column

		add_status_column(self.name)

	def on_trash(self) -> None:
		"""Block deletion of statuses that are in use and keep one open and one closed status."""
		self.validate_not_in_use()
		self.validate_open_and_closed_exist(exclude_self=True)

	def validate_not_in_use(self) -> None:
		"""A status used on any Work Item or Ticket Type cannot be deleted."""
		usage = (
			("Work Item", {"status": self.name}),
			("Ticket Type", {"default_status": self.name}),
			("Ticket Type Transition", {"from_status": self.name}),
			("Ticket Type Transition", {"to_status": self.name}),
		)
		for doctype, filters in usage:
			if frappe.db.exists(doctype, filters):
				frappe.throw(
					_("Status {0} is used on {1} and cannot be deleted").format(self.name, _(doctype))
				)

	def validate_open_and_closed_exist(self, exclude_self: bool) -> None:
		"""At least one active open and one active closed status must always exist."""
		for closed, label in ((0, _("open")), (1, _("closed"))):
			others = frappe.db.count(
				"Work Item Status", {"is_active": 1, "is_closed": closed, "name": ("!=", self.name)}
			)
			self_counts = not exclude_self and cint(self.is_active) and cint(self.is_closed) == closed
			if not others and not self_counts:
				frappe.throw(_("At least one active {0} status must exist").format(label))
