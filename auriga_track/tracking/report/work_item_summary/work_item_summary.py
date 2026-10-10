"""Work Item Summary: open, overdue, unassigned, closed in period and total per project."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, today


def execute(filters: dict | None = None) -> tuple:
	"""Return columns, data and a stacked bar chart; rows respect the user's project visibility."""
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters), None, get_chart(get_data(filters))


def get_columns() -> list[dict]:
	"""Report columns."""
	return [
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 220,
		},
		{"fieldname": "open", "label": _("Open"), "fieldtype": "Int", "width": 90},
		{"fieldname": "overdue", "label": _("Overdue"), "fieldtype": "Int", "width": 90},
		{"fieldname": "unassigned", "label": _("Unassigned"), "fieldtype": "Int", "width": 110},
		{"fieldname": "closed_in_period", "label": _("Closed in Period"), "fieldtype": "Int", "width": 130},
		{"fieldname": "total", "label": _("Total"), "fieldtype": "Int", "width": 90},
	]


def get_data(filters: frappe._dict) -> list[dict]:
	"""Aggregate work items per project (permission aware through frappe.get_list)."""
	item_filters = {k: filters[k] for k in ("project", "tracker", "release") if filters.get(k)}
	items = frappe.get_list(
		"Work Item",
		filters=item_filters,
		fields=["project", "is_closed", "assigned_to", "due_date", "closed_on"],
		limit_page_length=0,
	)
	start = getdate(filters.from_date) if filters.get("from_date") else None
	end = getdate(filters.to_date) if filters.get("to_date") else None
	by_project: dict[str, dict] = {}
	for item in items:
		row = by_project.setdefault(
			item.project,
			{
				"project": item.project,
				"open": 0,
				"overdue": 0,
				"unassigned": 0,
				"closed_in_period": 0,
				"total": 0,
			},
		)
		row["total"] += 1
		if cint(item.is_closed):
			if (
				item.closed_on
				and (not start or getdate(item.closed_on) >= start)
				and (not end or getdate(item.closed_on) <= end)
			):
				row["closed_in_period"] += 1
			continue
		row["open"] += 1
		row["overdue"] += int(bool(item.due_date and getdate(item.due_date) < getdate(today())))
		row["unassigned"] += int(not item.assigned_to)
	return sorted(by_project.values(), key=lambda r: r["project"])


def get_chart(data: list[dict]) -> dict:
	"""Stacked bar of open vs closed items per project."""
	return {
		"data": {
			"labels": [r["project"] for r in data],
			"datasets": [
				{"name": _("Open"), "values": [r["open"] for r in data]},
				{"name": _("Closed"), "values": [r["total"] - r["open"] for r in data]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}
