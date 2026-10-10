"""Work Item Category master (spec 3.6)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from auri_pms.tracking.utils import get_capabilities, has_capability


class WorkItemCategory(Document):
	"""A per-project category, optionally with a default assignee."""

	def validate(self) -> None:
		"""Check the capability to manage categories and the default assignee."""
		if not has_capability(self.project, "can_manage_categories"):
			frappe.throw(_("You are not allowed to manage categories in Project {0}").format(self.project))
		if self.default_assignee and not get_capabilities(
			self.project, self.default_assignee, members_only=True
		).get("can_be_assigned"):
			frappe.throw(
				_("{0} cannot be assigned work items in Project {1}").format(
					self.default_assignee, self.project
				)
			)

	def on_trash(self) -> None:
		"""Deleting a category needs the same capability as managing it."""
		if not has_capability(self.project, "can_manage_categories"):
			frappe.throw(_("You are not allowed to manage categories in Project {0}").format(self.project))
