"""PMS Activity Type master: what kind of work a Time Entry records."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class PMSActivityType(Document):
	"""An activity (Development, Testing, ...) picked when logging time."""

	def on_trash(self) -> None:
		"""An activity type used on a Time Entry cannot be deleted."""
		if frappe.db.exists("Time Entry", {"activity_type": self.name}):
			frappe.throw(_("Activity Type {0} is used on Time Entries and cannot be deleted").format(self.name))
