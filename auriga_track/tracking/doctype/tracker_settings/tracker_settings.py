"""Tracker Settings (Single, spec 3.1)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class TrackerSettings(Document):
	"""Global defaults and limits of Auri PMS."""

	def validate(self) -> None:
		"""Validate numeric limits and the default status."""
		for fieldname in ("time_entry_lock_days", "due_reminder_days"):
			if cint(self.get(fieldname)) < 0:
				frappe.throw(_("{0} cannot be negative").format(_(self.meta.get_label(fieldname))))
		for fieldname in ("max_hours_per_entry", "max_hours_per_day"):
			if flt(self.get(fieldname)) <= 0:
				frappe.throw(_("{0} must be greater than 0").format(_(self.meta.get_label(fieldname))))
		if cint(self.max_subtask_depth) < 1:
			frappe.throw(_("Max Subtask Depth must be at least 1"))
		if self.default_status and cint(
			frappe.db.get_value("Work Item Status", self.default_status, "is_closed")
		):
			frappe.throw(_("Default Status must be an open status"))

	def on_update(self) -> None:
		"""Drop cached capabilities (the public project role may have changed)."""
		from auriga_track.tracking.utils import clear_cache

		clear_cache()
