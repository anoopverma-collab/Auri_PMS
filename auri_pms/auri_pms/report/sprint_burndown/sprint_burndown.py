"""Sprint Burndown: remaining work per day against the ideal line."""

from __future__ import annotations

import frappe
from frappe import _

from auri_pms.auri_pms.utils import get_burndown


def execute(filters: dict | None = None) -> tuple:
	"""Return one row per sprint day and a line chart (ideal vs actual remaining)."""
	filters = frappe._dict(filters or {})
	if not filters.sprint:
		frappe.throw(_("Sprint is required"))
	if not frappe.has_permission("Sprint", "read", doc=filters.sprint):
		frappe.throw(_("You do not have access to {0}").format(filters.sprint), frappe.PermissionError)
	if filters.project and frappe.db.get_value("Sprint", filters.sprint, "project") != filters.project:
		frappe.throw(_("{0} does not belong to Project {1}").format(filters.sprint, filters.project))
	burndown = get_burndown(filters.sprint)
	unit = _("Hours") if burndown["unit"] == "hours" else _("Items")
	columns = [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{
			"fieldname": "ideal",
			"label": _("Ideal Remaining ({0})").format(unit),
			"fieldtype": "Float",
			"width": 180,
		},
		{
			"fieldname": "actual",
			"label": _("Actual Remaining ({0})").format(unit),
			"fieldtype": "Float",
			"width": 180,
		},
		{
			"fieldname": "completed",
			"label": _("Completed That Day ({0})").format(unit),
			"fieldtype": "Float",
			"width": 200,
		},
	]
	rows = burndown["rows"]
	# Frappe charts draw missing values as zero, so the chart stops at the last day with actual data.
	plotted = [r for r in rows if r["actual"] is not None]
	chart = {
		"data": {
			"labels": [str(r["date"]) for r in plotted],
			"datasets": [
				{"name": _("Ideal"), "values": [r["ideal"] for r in plotted]},
				{"name": _("Actual"), "values": [r["actual"] for r in plotted]},
			],
		},
		"type": "line",
		"lineOptions": {"regionFill": 0, "hideDots": 0},
	}
	return columns, rows, None, chart
