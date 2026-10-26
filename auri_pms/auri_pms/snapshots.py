# Copyright (c) 2026, Anoop Verma and contributors
# For license information, please see license.txt

"""Project-wise dashboard records: the Project Health figures saved per project, per week and per month."""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

DOCTYPE = "Project Dashboard Snapshot"


def take_snapshot(project: str, period_type: str = "Manual", on: str | None = None) -> str:
	"""Save today's dashboard of `project`; one snapshot per project, day and type (a repeat replaces it)."""
	from auri_pms.auri_pms.api import get_project_health

	on = str(getdate(on or today()))
	data = get_project_health(project)
	flow, time, status, risks = data.get("flow", {}), data.get("time", {}), data.get("status") or {}, data.get("risks", {})
	values = {
		"project": project,
		"snapshot_date": on,
		"period_type": period_type,
		"health_label": status.get("label"),
		"health_score": cint(status.get("score")),
		"completion_pct": flt(flow.get("completion_pct")),
		"open_tickets": cint(flow.get("open")),
		"closed_tickets": cint(flow.get("closed")),
		"overdue_tickets": cint(flow.get("overdue")),
		"spent_hours": flt(time.get("spent")),
		"billable_hours": flt(time.get("billable")),
		"open_risks": cint(risks.get("open")),
		"data": json.dumps(data, default=str),
	}
	existing = frappe.db.get_value(DOCTYPE, {"project": project, "snapshot_date": on, "period_type": period_type})
	doc = frappe.get_doc(DOCTYPE, existing) if existing else frappe.new_doc(DOCTYPE)
	doc.update(values)
	doc.save(ignore_permissions=True)
	return doc.name


def enabled_projects() -> list[str]:
	return frappe.get_all("Project", filters={"pms_enabled": 1}, pluck="name")


def _take_for_all(period_type: str) -> None:
	for project in enabled_projects():
		try:
			take_snapshot(project, period_type)
		except Exception:
			frappe.log_error(title=f"Dashboard snapshot failed for {project}")
	frappe.db.commit()


def weekly() -> None:
	"""Scheduled daily; keeps one snapshot per project on Mondays."""
	if getdate().weekday() == 0:
		_take_for_all("Weekly")


def monthly() -> None:
	"""Scheduled daily; keeps one snapshot per project on the 1st of the month."""
	if getdate().day == 1:
		_take_for_all("Monthly")


@frappe.whitelist()
def take_project_snapshot(project: str) -> str:
	"""Save a snapshot now (the *Save snapshot* button on the project page)."""
	from auri_pms.permissions import can_see_project

	frappe.has_permission(DOCTYPE, "create", throw=True)
	if not can_see_project(project):
		frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
	return take_snapshot(project, "Manual")


@frappe.whitelist()
def get_project_snapshots(project: str) -> list[dict]:
	"""History of one project, newest first, without the heavy data blob."""
	frappe.has_permission(DOCTYPE, "read", throw=True)
	from auri_pms.auri_pms.utils import is_allocated

	can_delete = frappe.has_permission(DOCTYPE, "create") and is_allocated(project)
	rows = frappe.get_list(
		DOCTYPE,
		filters={"project": project},
		fields=[
			"name", "snapshot_date", "period_type", "health_label", "health_score", "completion_pct",
			"open_tickets", "closed_tickets", "overdue_tickets", "spent_hours", "billable_hours", "open_risks",
		],
		order_by="snapshot_date desc, creation desc",
		limit=200,
	)
	for row in rows:
		row["can_delete"] = bool(can_delete)
	return rows


@frappe.whitelist()
def delete_project_snapshot(name: str) -> None:
	"""Remove one saved dashboard (a mistaken or test snapshot). Only people allocated to its project, or an admin."""
	from auri_pms.auri_pms.utils import is_allocated

	project = frappe.db.get_value(DOCTYPE, name, "project")
	if not project:
		frappe.throw(_("Snapshot {0} does not exist").format(name), frappe.DoesNotExistError)
	if not (frappe.has_permission(DOCTYPE, "create") and is_allocated(project)):
		frappe.throw(_("Only people allocated to {0} can delete its saved dashboards").format(project), frappe.PermissionError)
	frappe.delete_doc(DOCTYPE, name, ignore_permissions=True)  # whoever may save a snapshot of the project may remove one


@frappe.whitelist()
def get_project_snapshot(name: str) -> dict:
	"""One saved dashboard, as get_project_health returned it on that day."""
	doc = frappe.get_doc(DOCTYPE, name)
	doc.check_permission("read")
	return {"snapshot_date": doc.snapshot_date, "period_type": doc.period_type, "data": json.loads(doc.data or "{}")}
