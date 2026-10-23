"""Release Progress: roll-up of items and hours per release."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today

from auri_pms.auri_pms.utils import summary_card


def execute(filters: dict | None = None) -> tuple:
	"""Return columns and rows; the % Complete column renders as a progress bar."""
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, None, get_summary(data)


def get_summary(data: list[dict]) -> list[dict]:
	"""Releases, average completion, releases past their due date and the items still open."""
	late = sum(
		1 for r in data if r.days_left is not None and r.days_left < 0 and flt(r.percent_complete) < 100
	)
	return [
		summary_card(len(data), _("Releases"), indicator="Blue"),
		summary_card(
			sum(flt(r.percent_complete) for r in data) / len(data) if data else 0,
			_("Average Complete"),
			"Percent",
			"Green",
		),
		summary_card(late, _("Past Due"), indicator="Red" if late else "Green"),
		summary_card(sum(r["items"] - r["closed"] for r in data), _("Open Items"), indicator="Orange"),
	]


def get_columns() -> list[dict]:
	"""Report columns."""
	return [
		{
			"fieldname": "release",
			"label": _("Release"),
			"fieldtype": "Link",
			"options": "Release",
			"width": 170,
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 170,
		},
		{"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days_left", "label": _("Days Left"), "fieldtype": "Int", "width": 100},
		{"fieldname": "items", "label": _("Items"), "fieldtype": "Int", "width": 80},
		{"fieldname": "closed", "label": _("Closed"), "fieldtype": "Int", "width": 80},
		{"fieldname": "percent_complete", "label": _("% Complete"), "fieldtype": "Percent", "width": 140},
		{"fieldname": "estimated_hours", "label": _("Estimated Hours"), "fieldtype": "Float", "width": 130},
		{"fieldname": "spent_hours", "label": _("Spent Hours"), "fieldtype": "Float", "width": 120},
	]


def get_data(filters: frappe._dict) -> list[dict]:
	"""Releases visible to the user with their roll-up fields."""
	release_filters = {k: filters[k] for k in ("project", "status") if filters.get(k)}
	releases = frappe.get_list(
		"Release",
		filters=release_filters,
		fields=[
			"name as release",
			"project",
			"due_date",
			"total_items as items",
			"closed_items as closed",
			"percent_complete",
			"estimated_hours",
			"spent_hours",
		],
		order_by="due_date asc, name asc",
		limit_page_length=0,
	)
	releases.sort(key=lambda r: (r.due_date is None, r.due_date or "", r.release))  # undated releases last
	for row in releases:
		row["days_left"] = date_diff(getdate(row.due_date), getdate(today())) if row.due_date else None
	return releases
