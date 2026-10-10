"""Time Entry - hours logged against a project or work item (spec 3.10, R-28, R-38 .. R-44)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, today

from auri_pms.tracking.utils import (
	get_capabilities,
	get_settings,
	is_manager,
	recalc_chain,
	recalc_release,
	recalc_sprint,
)


class TimeEntry(Document):
	"""A single time log."""

	def validate(self) -> None:
		"""Run all server-side time rules."""
		self.old = self.get_doc_before_save()
		self.set_project_from_work_item()
		self.set_employee()
		self.validate_permission()
		self.validate_date()
		self.validate_lock()
		self.validate_hours()
		self.validate_work_item_open()

	def set_project_from_work_item(self) -> None:
		"""R-38: project comes from the work item and must match when given."""
		if not self.work_item:
			self.release = None
			return
		item = frappe.db.get_value("Work Item", self.work_item, ["project", "release"], as_dict=True)
		if self.project and self.project != item.project:
			frappe.throw(_("Project must match the work item's project"))
		self.project = item.project
		self.release = item.release

	def set_employee(self) -> None:
		"""Fetch the Employee linked to the user."""
		if self.user and not self.employee:
			self.employee = frappe.db.get_value("Employee", {"user_id": self.user}, "name")

	def validate_permission(self) -> None:
		"""R-39: can_log_time, and can_edit_others_time for entries of other users."""
		caps = get_capabilities(self.project)
		if not caps["can_log_time"]:
			frappe.throw(_("You are not allowed to log time in Project {0}").format(self.project))
		owners = {self.user, self.old.user if self.old else self.user}
		if owners != {frappe.session.user} and not caps["can_edit_others_time"]:
			frappe.throw(_("You can only change your own time entries"))

	def validate_date(self) -> None:
		"""R-42: no future dates."""
		if getdate(self.date) > getdate(today()):
			frappe.throw(_("Time cannot be logged for a future date"))

	def validate_lock(self) -> None:
		"""R-43: entries older than time_entry_lock_days are locked (manager bypass)."""
		dates = [self.date]
		if self.old:
			dates.append(self.old.date)
		check_lock(dates)

	def validate_hours(self) -> None:
		"""R-41: positive, within the per-entry and per-day limits."""
		settings = get_settings()
		hours = flt(self.hours)
		if hours <= 0:
			frappe.throw(_("Hours must be greater than 0"))
		if hours > flt(settings.max_hours_per_entry):
			frappe.throw(_("Hours per entry cannot exceed {0}").format(settings.max_hours_per_entry))
		logged = flt(
			frappe.db.sql(
				"select coalesce(sum(hours), 0) from `tabTime Entry` where user = %s and date = %s and name != %s",
				(self.user, self.date, self.name or ""),
			)[0][0]
		)
		if logged + hours > flt(settings.max_hours_per_day):
			frappe.throw(
				_("{0} would log {1} hours on {2}; the daily limit is {3}").format(
					self.user, logged + hours, self.date, settings.max_hours_per_day
				)
			)

	def validate_work_item_open(self) -> None:
		"""R-44: no time on closed work items unless allowed."""
		if not self.work_item or cint(get_settings().allow_time_on_closed_items):
			return
		if not self.old or self.old.work_item != self.work_item:
			if cint(frappe.db.get_value("Work Item", self.work_item, "is_closed")):
				frappe.throw(_("Cannot log time on closed work item {0}").format(self.work_item))

	def on_update(self) -> None:
		"""R-28, R-30: roll the hours up to the item, its ancestors and releases."""
		items = {self.work_item}
		if self.old and self.old.work_item:
			items.add(self.old.work_item)
		rollup_items(items)

	def on_trash(self) -> None:
		"""R-39 and R-43 apply to deletion as well."""
		self.old = None
		self.validate_permission()
		check_lock([self.date])

	def after_delete(self) -> None:
		"""Recalculate the totals the deleted entry contributed to."""
		rollup_items({self.work_item})


def check_lock(dates: list) -> None:
	"""Throw if any date falls before today minus time_entry_lock_days (R-43). Managers bypass."""
	lock_days = cint(get_settings().time_entry_lock_days)
	if not lock_days or is_manager():
		return
	cutoff = getdate(add_days(today(), -lock_days))
	if any(getdate(d) < cutoff for d in dates if d):
		frappe.throw(_("Time entries older than {0} days are locked").format(lock_days))


def rollup_items(work_items: set[str | None]) -> None:
	"""Recalculate totals for work items (and ancestors), then their releases."""
	releases, sprints = set(), set()
	for item in filter(None, work_items):
		recalc_chain(item)
		release, sprint = frappe.db.get_value("Work Item", item, ["release", "sprint"])
		releases.add(release)
		sprints.add(sprint)
	for release in releases:
		recalc_release(release)
	for sprint in sprints:
		recalc_sprint(sprint)
