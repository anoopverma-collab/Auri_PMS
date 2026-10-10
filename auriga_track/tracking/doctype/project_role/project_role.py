"""Project Role master (spec 3.5)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class ProjectRole(Document):
	"""A per-project role carrying the capability flags."""

	def on_update(self) -> None:
		"""Drop cached capabilities when a role changes."""
		from auriga_track.tracking.utils import clear_cache

		clear_cache()

	def on_trash(self) -> None:
		"""A role used in any Project Member row or in Tracker Settings cannot be deleted."""
		if frappe.db.exists("Project Member", {"project_role": self.name}):
			frappe.throw(
				_("Project Role {0} is used by project members and cannot be deleted").format(self.name)
			)
		if frappe.db.get_single_value("Tracker Settings", "public_project_role") == self.name:
			frappe.throw(
				_("Project Role {0} is used in Tracker Settings and cannot be deleted").format(self.name)
			)
		if frappe.db.exists("Ticket Type Transition", {"project_role": self.name}):
			frappe.throw(
				_("Project Role {0} is used in a tracker workflow and cannot be deleted").format(self.name)
			)
