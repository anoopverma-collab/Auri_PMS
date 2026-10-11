"""Client Dependencies: open tickets that wait on the client, longest wait first."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, today


def execute(filters: dict | None = None) -> tuple:
	"""Return columns, rows and a bar chart of waiting tickets per project (permission aware)."""
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data)


def get_columns() -> list[dict]:
	"""Report columns."""
	return [
		{
			"fieldname": "item",
			"label": _("Ticket"),
			"fieldtype": "Link",
			"options": "Work Item",
			"width": 120,
		},
		{"fieldname": "subject", "label": _("Summary"), "fieldtype": "Data", "width": 260},
		{"fieldname": "module", "label": _("Module"), "fieldtype": "Data", "width": 130},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 160,
		},
		{
			"fieldname": "ticket_type",
			"label": _("Ticket Type"),
			"fieldtype": "Link",
			"options": "Ticket Type",
			"width": 110,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Link",
			"options": "Work Item Status",
			"width": 110,
		},
		{"fieldname": "note", "label": _("What We Need From the Client"), "fieldtype": "Data", "width": 280},
		{"fieldname": "since", "label": _("Waiting Since"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days_waiting", "label": _("Days Waiting"), "fieldtype": "Int", "width": 110},
		{
			"fieldname": "assigned_to",
			"label": _("Assigned To"),
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
		{"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "priority", "label": _("Priority"), "fieldtype": "Data", "width": 90},
	]


def get_data(filters: frappe._dict) -> list[dict]:
	"""Open client-dependent tickets, longest wait first."""
	item_filters = {"dependent_on_client": 1, "is_closed": 0}
	for key in ("project", "assigned_to"):
		if filters.get(key):
			item_filters[key] = filters[key]
	rows = frappe.get_list(
		"Work Item",
		filters=item_filters,
		fields=[
			"name as item",
			"subject",
			"project",
			"tracker as ticket_type",
			"project_module",
			"status",
			"priority",
			"assigned_to",
			"due_date",
			"client_dependency_note as note",
			"client_dependency_since as since",
		],
		limit_page_length=0,
	)
	labels = {
		m.name: m.module_name
		for m in frappe.get_all(
			"Project Module",
			filters={"name": ["in", list({r.project_module for r in rows if r.project_module}) or [""]]},
			fields=["name", "module_name"],
		)
	}
	today_ = getdate(today())
	for row in rows:
		row["module"] = labels.get(row.pop("project_module", None)) or ""
		row["days_waiting"] = (today_ - getdate(row.since)).days if row.since else 0
	minimum = cint(filters.get("min_days"))
	return sorted(
		(r for r in rows if r["days_waiting"] >= minimum), key=lambda r: (-r["days_waiting"], r["item"])
	)


def get_chart(data: list[dict]) -> dict:
	"""Bar chart: tickets waiting on the client per project."""
	counts: dict[str, int] = {}
	for row in data:
		counts[row["project"]] = counts.get(row["project"], 0) + 1
	return {
		"data": {
			"labels": list(counts),
			"datasets": [{"name": _("Waiting on client"), "values": list(counts.values())}],
		},
		"type": "bar",
	}
