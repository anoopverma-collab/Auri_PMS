"""Sprint Summary: dates, progress and hours per sprint."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, today


def execute(filters: dict | None = None) -> tuple:
	"""Return columns, rows and a stacked bar chart of closed vs open items per sprint."""
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data)


def get_columns() -> list[dict]:
	"""Report columns."""
	return [
		{"fieldname": "sprint", "label": _("Sprint"), "fieldtype": "Link", "options": "Sprint", "width": 170},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 170,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "start_date", "label": _("Start"), "fieldtype": "Date", "width": 100},
		{"fieldname": "end_date", "label": _("End"), "fieldtype": "Date", "width": 100},
		{"fieldname": "days_left", "label": _("Days Left"), "fieldtype": "Int", "width": 95},
		{"fieldname": "items", "label": _("Items"), "fieldtype": "Int", "width": 80},
		{"fieldname": "closed", "label": _("Closed"), "fieldtype": "Int", "width": 80},
		{"fieldname": "percent_complete", "label": _("% Complete"), "fieldtype": "Percent", "width": 130},
		{"fieldname": "estimated_hours", "label": _("Estimated Hours"), "fieldtype": "Float", "width": 125},
		{"fieldname": "spent_hours", "label": _("Spent Hours"), "fieldtype": "Float", "width": 115},
		{"fieldname": "goal", "label": _("Goal"), "fieldtype": "Data", "width": 260},
	]


def get_data(filters: frappe._dict) -> list[dict]:
	"""Sprints visible to the user (permission aware through frappe.get_list)."""
	sprint_filters = {k: filters[k] for k in ("project", "status") if filters.get(k)}
	rows = frappe.get_list(
		"Sprint",
		filters=sprint_filters,
		fields=[
			"name as sprint",
			"project",
			"status",
			"start_date",
			"end_date",
			"total_items as items",
			"closed_items as closed",
			"percent_complete",
			"estimated_hours",
			"spent_hours",
			"goal",
		],
		order_by="start_date desc, name asc",
		limit_page_length=0,
	)
	for row in rows:
		row["days_left"] = (
			max(date_diff(getdate(row.end_date), getdate(today())), 0) if row.status != "Completed" else 0
		)
	return rows


def get_chart(data: list[dict]) -> dict:
	"""Stacked bar: closed and open items per sprint."""
	return {
		"data": {
			"labels": [r["sprint"] for r in data],
			"datasets": [
				{"name": _("Closed"), "values": [r["closed"] for r in data]},
				{"name": _("Open"), "values": [r["items"] - r["closed"] for r in data]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}
