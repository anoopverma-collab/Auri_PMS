"""Overdue Work Items: open items past their due date."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, today


def execute(filters: dict | None = None) -> tuple:
	"""Return columns and rows of overdue open items the user may see."""
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


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
	return rows
