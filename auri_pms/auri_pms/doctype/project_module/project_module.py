"""Project Module master: the parts of a project (for example Sales, Stock or Accounts) a ticket can belong to."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from auri_pms.auri_pms.utils import can_manage_modules, has_capability


class ProjectModule(Document):
	"""A shared module that groups work items by the area of the product they are about; projects tag the ones they use."""

	def validate(self) -> None:
		"""Managing modules needs the same capability as managing categories."""
		self.validate_can_manage()

	def validate_can_manage(self) -> None:
		"""Admins, Auri PMS Managers and project managers maintain the shared modules (a legacy project-bound one follows its project)."""
		if not self.project:
			if not can_manage_modules():
				frappe.throw(_("You are not allowed to manage modules"))
			return
		if not has_capability(self.project, "can_manage_categories"):
			frappe.throw(_("You are not allowed to manage modules in Project {0}").format(self.project))

	def on_trash(self) -> None:
		"""Deleting a module needs the same capability as managing it."""
		self.validate_can_manage()
