"""Tracker master (spec 3.3, 3.4)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class Tracker(Document):
	"""A work item type (Bug, Feature ...) with an optional status workflow."""

	def validate(self) -> None:
		"""Validate default status and transition rows."""
		self.validate_default_status()
		self.validate_transitions()

	def validate_default_status(self) -> None:
		"""The default status must be an open status."""
		if self.default_status and cint(
			frappe.db.get_value("Work Item Status", self.default_status, "is_closed")
		):
			frappe.throw(_("Default Status must be an open status"))

	def validate_transitions(self) -> None:
		"""From and To must differ and rows may not repeat (same from, to, role)."""
		seen = set()
		for row in self.transitions:
			if row.from_status == row.to_status:
				frappe.throw(_("Row {0}: To status must differ from From status").format(row.idx))
			key = (row.from_status, row.to_status, row.project_role or "")
			if key in seen:
				frappe.throw(_("Row {0}: duplicate transition").format(row.idx))
			seen.add(key)
