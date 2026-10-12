"""PMS Settings (Single, spec 3.1)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class PMSSettings(Document):
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
		self.validate_risk_levels()
		self.validate_health_thresholds()
		if self.default_status and cint(
			frappe.db.get_value("Work Item Status", self.default_status, "is_closed")
		):
			frappe.throw(_("Default Status must be an open status"))

	def validate_risk_levels(self) -> None:
		"""Medium < High < Critical, all inside the 1-25 score range."""
		medium, high, critical = (
			cint(self.risk_medium_from),
			cint(self.risk_high_from),
			cint(self.risk_critical_from),
		)
		if not 1 <= medium < high < critical <= 25:
			frappe.throw(_("Risk thresholds must increase from Medium to Critical and stay between 1 and 25"))

	def validate_health_thresholds(self) -> None:
		"""Percentages stay between 0 and 100 and Off Track is never below At Risk."""
		for amber, red in (
			("overdue_amber_pct", "overdue_red_pct"),
			("burndown_amber_pct", "burndown_red_pct"),
		):
			if not 0 <= cint(self.get(amber)) <= cint(self.get(red)) <= 100:
				frappe.throw(
					_("{0} must be between 0 and {1}, which in turn cannot exceed 100").format(
						_(self.meta.get_label(amber)), _(self.meta.get_label(red))
					)
				)
		for fieldname in ("effort_ahead_amber_pct", "release_progress_pct"):
			if not 0 <= cint(self.get(fieldname)) <= 100:
				frappe.throw(_("{0} must be between 0 and 100").format(_(self.meta.get_label(fieldname))))
		if self.report_default_recipients:
			from auri_pms.auri_pms.status_report import parse_recipients

			parse_recipients(self.report_default_recipients)  # raises on an invalid or too long list
		for fieldname in (
			"release_due_soon_days",
			"backlog_growth_min_created",
			"score_red_penalty",
			"score_amber_penalty",
		):
			if cint(self.get(fieldname)) < 0:
				frappe.throw(_("{0} cannot be negative").format(_(self.meta.get_label(fieldname))))
		if flt(self.backlog_growth_ratio) < 1:
			frappe.throw(_("{0} must be at least 1").format(_(self.meta.get_label("backlog_growth_ratio"))))

	def on_update(self) -> None:
		"""Drop cached capabilities (the public project role may have changed)."""
		from auri_pms.auri_pms.utils import clear_cache

		clear_cache()
