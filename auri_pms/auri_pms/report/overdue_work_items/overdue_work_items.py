"""Overdue Work Items: open items past their due date."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, today

from auri_pms.auri_pms.utils import summary_card


def execute(filters: dict | None = None) -> tuple:
	"""Return columns and rows of overdue open items the user may see."""
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data), get_summary(data)


def get_summary(data: list[dict]) -> list[dict]:
	"""Overdue count, how long the oldest has waited, and how many are urgent."""
	urgent = sum(1 for r in data if r.priority in ("Urgent", "Immediate"))
	return [
		summary_card(len(data), _("Overdue Items"), indicator="Red" if data else "Green"),
		summary_card(max((r.days_overdue for r in data), default=0), _("Oldest (days)"), indicator="Orange"),
		summary_card(urgent, _("Urgent or Immediate"), indicator="Red" if urgent else "Gray"),
		summary_card(
			len({r.assigned_to for r in data if r.assigned_to}), _("People Affected"), indicator="Blue"
		),
	]


def get_columns() -> list[dict]:
	"""Report columns."""
	return [
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Link", "options": "Work Item", "width": 120},
		{"fieldname": "subject", "label": _("Subject"), "fieldtype": "Data", "width": 280},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 170,
		},
		{
			"fieldname": "assigned_to",
			"label": _("Assigned To"),
			"fieldtype": "Link",
			"options": "User",
			"width": 170,
		},
		{"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days_overdue", "label": _("Days Overdue"), "fieldtype": "Int", "width": 120},
		{"fieldname": "age_band", "label": _("Age Band"), "fieldtype": "Data", "width": 110},
		{"fieldname": "priority", "label": _("Priority"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Link",
			"options": "Work Item Status",
			"width": 120,
		},
	]


def get_data(filters: frappe._dict) -> list[dict]:
	"""Open items with a due date before today (permission aware)."""
	item_filters = {"is_closed": 0, "due_date": ["<", today()]}
	for key in ("project", "assigned_to"):
		if filters.get(key):
			item_filters[key] = filters[key]
	rows = frappe.get_list(
		"Work Item",
		filters=item_filters,
		fields=["name as item", "subject", "project", "assigned_to", "due_date", "priority", "status"],
		order_by="due_date asc, name asc",
		limit_page_length=0,
	)
	for row in rows:
		row["days_overdue"] = date_diff(getdate(today()), getdate(row.due_date))
		row["age_band"] = age_band(row["days_overdue"])
	return rows


def age_band(days: int) -> str:
	"""How long an item has been overdue: up to a week, up to a month, or longer."""
	return _("1-7 days") if days <= 7 else _("8-30 days") if days <= 30 else _("Over 30 days")


def get_chart(data: list[dict]) -> dict:
	"""Bar chart: overdue items per age band."""
	bands = [_("1-7 days"), _("8-30 days"), _("Over 30 days")]
	return {
		"data": {
			"labels": bands,
			"datasets": [
				{
					"name": _("Overdue items"),
					"values": [sum(1 for r in data if r.age_band == b) for b in bands],
				}
			],
		},
		"type": "bar",
		"colors": ["#ef4444"],
	}
