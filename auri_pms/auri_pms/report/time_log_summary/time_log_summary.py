"""Time Log Summary: hours and entries grouped by user, project, activity or work item."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from auri_pms.auri_pms.utils import summary_card

GROUP_FIELDS = {"User": "user", "Project": "project", "Activity": "activity_type", "Work Item": "work_item"}
GROUP_OPTIONS = {"User": "User", "Project": "Project", "Activity": "Activity Type", "Work Item": "Work Item"}


def execute(filters: dict | None = None) -> tuple:
	"""Return columns, data and a bar chart of hours per group."""
	filters = frappe._dict(filters or {})
	if not filters.from_date or not filters.to_date:
		frappe.throw(_("From Date and To Date are required"))
	group_by = filters.group_by or "User"
	data = get_data(filters, group_by)
	return get_columns(group_by), data, None, get_chart(data), get_summary(data)


def get_summary(data: list[dict]) -> list[dict]:
	"""Total hours, the billable share and the number of entries."""
	total = sum(r["hours"] for r in data)
	billable = sum(r["billable_hours"] for r in data)
	return [
		summary_card(total, _("Total Hours"), "Float", "Blue"),
		summary_card(billable, _("Billable Hours"), "Float", "Green"),
		summary_card(
			round(billable / total * 100, 1) if total else 0, _("Billable Share"), "Percent", "Green"
		),
		summary_card(sum(r["entries"] for r in data), _("Entries"), indicator="Gray"),
	]


def get_columns(group_by: str) -> list[dict]:
	"""Report columns; Estimated only applies when grouping by work item."""
	columns = [
		{
			"fieldname": "group",
			"label": _(group_by),
			"fieldtype": "Link",
			"options": GROUP_OPTIONS[group_by],
			"width": 260,
		},
		{"fieldname": "hours", "label": _("Hours"), "fieldtype": "Float", "width": 110},
		{"fieldname": "entries", "label": _("Entries"), "fieldtype": "Int", "width": 100},
		{"fieldname": "billable_hours", "label": _("Billable Hours"), "fieldtype": "Float", "width": 130},
		{
			"fieldname": "non_billable_hours",
			"label": _("Non-billable Hours"),
			"fieldtype": "Float",
			"width": 150,
		},
		{"fieldname": "pct_billable", "label": _("% Billable"), "fieldtype": "Percent", "width": 110},
	]
	if group_by == "Work Item":
		columns.append(
			{"fieldname": "estimated", "label": _("Estimated"), "fieldtype": "Float", "width": 110}
		)
	return columns


def get_data(filters: frappe._dict, group_by: str) -> list[dict]:
	"""Aggregate time entries (permission aware through frappe.get_list)."""
	field = GROUP_FIELDS[group_by]
	entry_filters = [["date", "between", [filters.from_date, filters.to_date]]]
	for key in ("project", "user"):
		if filters.get(key):
			entry_filters.append([key, "=", filters[key]])
	if filters.get("billable"):
		entry_filters.append(["is_billable", "=", 1 if filters.billable == "Billable" else 0])
	entries = frappe.get_list(
		"Time Entry", filters=entry_filters, fields=[field, "hours", "is_billable"], limit_page_length=0
	)
	groups: dict[str, dict] = {}
	for entry in entries:
		key = entry.get(field) or _("(none)")
		row = groups.setdefault(
			key,
			{
				"group": entry.get(field),
				"hours": 0.0,
				"entries": 0,
				"billable_hours": 0.0,
				"non_billable_hours": 0.0,
			},
		)
		row["hours"] += flt(entry.hours)
		row["billable_hours" if entry.is_billable else "non_billable_hours"] += flt(entry.hours)
		row["entries"] += 1
	for row in groups.values():
		row["pct_billable"] = round(row["billable_hours"] / row["hours"] * 100, 1) if row["hours"] else 0
	rows = sorted(groups.values(), key=lambda r: -r["hours"])
	if group_by == "Work Item" and rows:
		estimates = dict(
			frappe.get_list(
				"Work Item",
				filters={"name": ["in", [r["group"] for r in rows if r["group"]]]},
				fields=["name", "estimated_hours"],
				as_list=True,
				limit_page_length=0,
			)
		)
		for row in rows:
			row["estimated"] = flt(estimates.get(row["group"]))
	return rows


def get_chart(data: list[dict]) -> dict:
	"""Bar chart of hours per group."""
	return {
		"data": {
			"labels": [r["group"] or _("(none)") for r in data],
			"datasets": [{"name": _("Hours"), "values": [r["hours"] for r in data]}],
		},
		"type": "bar",
	}
