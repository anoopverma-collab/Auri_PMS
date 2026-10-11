"""Whitelisted API of Auri PMS (spec 5 R-18, section 6)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today

from auri_pms.permissions import can_see_project
from auri_pms.tracking.utils import (
	get_capabilities,
	get_descendants,
	get_enabled_trackers,
	is_manager,
	nearest_indicator,
	transition_allowed,
)


@frappe.whitelist()
def get_allowed_statuses(work_item: str | None = None, doc: str | dict | None = None) -> list[str]:
	"""Return the statuses the current user may move ``work_item`` to (R-18).

	For an unsaved item pass ``doc`` (tracker, project, status); the open active statuses are returned.
	"""
	if work_item and frappe.db.exists("Work Item", work_item):
		if not frappe.has_permission("Work Item", "read", doc=work_item):
			frappe.throw(_("You do not have access to {0}").format(work_item), frappe.PermissionError)
		item = frappe.db.get_value("Work Item", work_item, ["tracker", "project", "status"], as_dict=True)
	else:
		item = frappe._dict(frappe.parse_json(doc) if isinstance(doc, str) else (doc or {}))
		item.status = None
	statuses = frappe.get_all(
		"Work Item Status",
		filters={"is_active": 1},
		fields=["name", "is_closed"],
		order_by="sequence asc, name asc",
	)
	if not item.status:
		return [s.name for s in statuses if not cint(s.is_closed)]
	return [
		s.name
		for s in statuses
		if s.name != item.status and transition_allowed(item.tracker, item.status, s.name, item.project)
	]


def _like(txt: str | None) -> str:
	return f"%{txt or ''}%"


@frappe.whitelist()
def status_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for Work Item.status: the current status plus the allowed next statuses."""
	filters = frappe._dict(filters or {})
	if filters.work_item and frappe.db.exists("Work Item", filters.work_item):
		allowed = get_allowed_statuses(filters.work_item)
		allowed = [frappe.db.get_value("Work Item", filters.work_item, "status"), *allowed]
	else:
		allowed = get_allowed_statuses(None, {"tracker": filters.tracker, "project": filters.project})
	return [[s] for s in allowed if not txt or txt.lower() in s.lower()]


@frappe.whitelist()
def tracker_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for Work Item.tracker: active trackers enabled on the project."""
	project = (filters or {}).get("project")
	names = (
		get_enabled_trackers(project)
		if project
		else frappe.get_all("Ticket Type", {"is_active": 1}, pluck="name")
	)
	return [
		[n]
		for n in frappe.get_all(
			"Ticket Type",
			filters={"name": ["in", names or [""]], "is_active": 1, "tracker_name": ["like", _like(txt)]},
			pluck="name",
			order_by="name asc",
			limit_start=cint(start),
			limit_page_length=cint(page_len) or 20,
		)
	]


@frappe.whitelist()
def assignee_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for Work Item.assigned_to: enabled members whose role has can_be_assigned."""
	project = (filters or {}).get("project")
	if not project or not can_see_project(project):
		return []
	return frappe.db.sql(
		"""
		select u.name, u.full_name
		from `tabProject Member` pm
		join `tabProject Role` pr on pr.name = pm.project_role and pr.can_be_assigned = 1
		join `tabUser` u on u.name = pm.user and u.enabled = 1
		where pm.parent = %(project)s and pm.parenttype = 'Project'
			and (u.name like %(txt)s or u.full_name like %(txt)s)
		order by u.full_name
		limit %(start)s, %(page_len)s
		""",
		{"project": project, "txt": _like(txt), "start": cint(start), "page_len": cint(page_len) or 20},
	)


@frappe.whitelist()
def parent_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for Work Item.parent_work_item: same project, not self, not a descendant."""
	filters = frappe._dict(filters or {})
	if not filters.project:
		return []
	excluded = [filters.work_item, *get_descendants(filters.work_item)] if filters.work_item else []
	return frappe.get_list(
		"Work Item",
		filters={"project": filters.project, "name": ["not in", excluded or [""]]},
		or_filters={"name": ["like", _like(txt)], "subject": ["like", _like(txt)]},
		fields=["name", "subject"],
		order_by="modified desc",
		limit_start=cint(start),
		limit_page_length=cint(page_len) or 20,
		as_list=True,
	)


@frappe.whitelist()
def project_create_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for Work Item.project: projects (with an identifier) the user may create items in."""
	candidates = frappe.get_list(
		"Project",
		filters={"tracker_identifier": ["is", "set"]},
		or_filters={"name": ["like", _like(txt)], "project_name": ["like", _like(txt)]},
		fields=["name", "project_name"],
		order_by="modified desc",
		limit_page_length=200,
	)
	rows = [
		[p.name, p.project_name]
		for p in candidates
		if is_manager() or get_capabilities(p.name)["can_create_items"]
	]
	start, page_len = cint(start), cint(page_len) or 20
	return rows[start : start + page_len]


@frappe.whitelist()
def log_time(
	work_item: str,
	hours: float,
	activity_type: str,
	date: str | None = None,
	comment: str | None = None,
	is_billable: int | str = 1,
) -> str:
	"""Create a Time Entry for the current user on ``work_item`` and return its name."""
	entry = frappe.get_doc(
		{
			"doctype": "Time Entry",
			"work_item": work_item,
			"user": frappe.session.user,
			"hours": flt(hours),
			"activity_type": activity_type,
			"date": getdate(date or today()),
			"comment": comment,
			"is_billable": cint(is_billable),
		}
	)
	entry.insert()
	return entry.name


@frappe.whitelist()
def get_status_actions(work_item: str) -> dict:
	"""Return the statuses the Close and Reopen buttons move ``work_item`` to (None when not offered)."""
	allowed = set(get_allowed_statuses(work_item))
	is_closed = cint(frappe.db.get_value("Work Item", work_item, "is_closed"))
	statuses = frappe.get_all(
		"Work Item Status",
		filters={"is_active": 1, "name": ["in", list(allowed) or [""]]},
		fields=["name", "is_closed"],
		order_by="sequence asc",
	)
	close = next((s.name for s in statuses if cint(s.is_closed)), None)
	reopen = next((s.name for s in statuses if not cint(s.is_closed)), None)
	return {"close": None if is_closed else close, "reopen": reopen if is_closed else None}


@frappe.whitelist()
def get_status_indicators() -> dict[str, str]:
	"""Return {status: Desk indicator colour} for list and form indicators."""
	return {
		s.name: nearest_indicator(s.color)
		for s in frappe.get_all("Work Item Status", fields=["name", "color"], limit_page_length=0)
	}


@frappe.whitelist()
def move_to_sprint(work_items: str | list, sprint: str | None = None) -> dict:
	"""Move work items to ``sprint`` (or back to the backlog when blank); every item is saved with all rules.

	Returns ``{"moved": n, "failed": [{"name", "error"}]}``. A failing item is rolled back on its own.
	"""
	names = frappe.parse_json(work_items) if isinstance(work_items, str) else work_items
	moved, failed = 0, []
	for name in names:
		message_count = len(getattr(frappe.local, "message_log", None) or [])
		frappe.db.savepoint("move_to_sprint")
		try:
			doc = frappe.get_doc("Work Item", name)
			doc.sprint = sprint or None
			doc.save()
			moved += 1
		except (frappe.ValidationError, frappe.PermissionError) as exc:
			frappe.db.rollback(save_point="move_to_sprint")
			del frappe.local.message_log[message_count:]  # reported in the result, not as popups
			failed.append({"name": name, "error": frappe.utils.strip_html(str(exc))})
	return {"moved": moved, "failed": failed}


# --------------------------------------------------------------------------- Project Hub
@frappe.whitelist()
def get_hub_projects() -> list[dict]:
	"""Projects the user can see, with the numbers shown on the Project Hub cards."""
	projects = frappe.get_list(
		"Project",
		fields=["name", "project_name", "tracker_identifier", "status", "is_public"],
		order_by="modified desc",
		limit_page_length=0,
	)
	if not projects:
		return []
	names = [p.name for p in projects]
	today_ = getdate(today())
	stats = {n: {"open": 0, "overdue": 0, "mine": 0, "total": 0} for n in names}
	for item in frappe.get_list(
		"Work Item",
		filters={"project": ["in", names]},
		fields=["project", "is_closed", "due_date", "assigned_to"],
		limit_page_length=0,
	):
		row = stats[item.project]
		row["total"] += 1
		if not cint(item.is_closed):
			row["open"] += 1
			row["overdue"] += int(bool(item.due_date and getdate(item.due_date) < today_))
			row["mine"] += int(item.assigned_to == frappe.session.user)
	sprints = {
		s.project: s
		for s in frappe.get_list(
			"Sprint",
			filters={"project": ["in", names], "status": "Active"},
			fields=["name", "project", "percent_complete", "end_date"],
			limit_page_length=0,
		)
	}
	members: dict[str, int] = {}
	for row in frappe.get_all(
		"Project Member", filters={"parent": ["in", names], "parenttype": "Project"}, fields=["parent"]
	):
		members[row.parent] = members.get(row.parent, 0) + 1
	for project in projects:
		project.update(stats[project.name])
		project["members"] = members.get(project.name, 0)
		project["active_sprint"] = sprints.get(project.name)
	return projects


@frappe.whitelist()
def get_project_hub(project: str) -> dict:
	"""Everything the Project Hub shows for one project (visibility rules apply)."""
	from auri_pms.permissions import can_see_project
	from auri_pms.tracking.utils import get_burndown

	if not frappe.db.exists("Project", project) or not can_see_project(project):
		frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
	info = frappe.db.get_value(
		"Project",
		project,
		["name", "project_name", "tracker_identifier", "status", "is_public"],
		as_dict=True,
	)
	caps = get_capabilities(project)
	user, today_ = frappe.session.user, getdate(today())
	items = frappe.get_list(
		"Work Item",
		filters={"project": project},
		fields=[
			"name",
			"subject",
			"status",
			"priority",
			"tracker",
			"project_module",
			"assigned_to",
			"due_date",
			"is_closed",
			"modified",
			"sprint",
			"done_percent",
			"dependent_on_client",
			"client_dependency_note",
			"client_dependency_since",
		],
		order_by="modified desc",
		limit_page_length=0,
	)
	open_items = [i for i in items if not cint(i.is_closed)]
	week_start = add_days(today_, -today_.weekday())
	hours = frappe.get_list(
		"Time Entry", filters={"project": project}, fields=["hours", "date", "user"], limit_page_length=0
	)
	numbers = {
		"total": len(items),
		"open": len(open_items),
		"closed": len(items) - len(open_items),
		"overdue": sum(1 for i in open_items if i.due_date and getdate(i.due_date) < today_),
		"unassigned": sum(1 for i in open_items if not i.assigned_to),
		"client_dependent": sum(1 for i in open_items if cint(i.dependent_on_client)),
		"client_oldest_days": max(
			[
				(today_ - getdate(i.client_dependency_since)).days
				for i in open_items
				if cint(i.dependent_on_client) and i.client_dependency_since
			],
			default=None,
		),
		"mine": sum(1 for i in open_items if i.assigned_to == user),
		"hours_total": flt(sum(flt(h.hours) for h in hours), 2),
		"hours_week": flt(sum(flt(h.hours) for h in hours if getdate(h.date) >= week_start), 2),
		"hours_mine": flt(sum(flt(h.hours) for h in hours if h.user == user), 2),
	}

	from auri_pms.tracking.health import count_by, count_by_module, module_labels
	from auri_pms.tracking.risk import risk_summary

	sprints = frappe.get_list(
		"Sprint",
		filters={"project": project},
		fields=[
			"name",
			"sprint_name",
			"status",
			"start_date",
			"end_date",
			"percent_complete",
			"total_items",
			"closed_items",
			"goal",
		],
		order_by="start_date desc",
		limit_page_length=0,
	)
	active = next((s for s in sprints if s.status == "Active"), None)
	if active:
		burndown = get_burndown(active.name)
		active["burndown"] = {
			"unit": burndown["unit"],
			"rows": [
				{"date": str(r["date"]), "ideal": r["ideal"], "actual": r["actual"]}
				for r in burndown["rows"]
				if r["actual"] is not None
			],
		}
	releases = frappe.get_list(
		"Release",
		filters={"project": project},
		fields=["name", "release_name", "status", "due_date", "percent_complete", "total_items"],
		order_by="due_date asc",
		limit_page_length=0,
	)
	members = frappe.get_all(
		"Project Member",
		filters={"parent": project, "parenttype": "Project"},
		fields=["user", "full_name", "project_role"],
		order_by="idx asc",
	)
	return frappe._dict(
		project=info,
		capabilities=caps,
		numbers=numbers,
		by_status=count_by(open_items, "status", ordered_by_status=True),
		by_tracker=count_by(open_items, "tracker"),
		by_module=count_by_module(open_items, module_labels(project)),
		risks=risk_summary(project),
		by_priority=count_by(open_items, "priority"),
		active_sprint=active,
		sprints=sprints,
		releases=releases,
		members=members,
		recent_items=items[:10],
		client_tickets=[
			{
				"name": i.name,
				"subject": i.subject,
				"note": i.client_dependency_note,
				"since": i.client_dependency_since,
				"days": (today_ - getdate(i.client_dependency_since)).days
				if i.client_dependency_since
				else 0,
				"status": i.status,
				"priority": i.priority,
				"due_date": i.due_date,
			}
			for i in sorted(
				(i for i in open_items if cint(i.dependent_on_client)),
				key=lambda i: str(i.client_dependency_since or "9999"),
			)[:15]
		],
		backlog_items=sum(1 for i in open_items if not i.sprint),
		backlog_client=sum(1 for i in open_items if not i.sprint and cint(i.dependent_on_client)),
	)


@frappe.whitelist()
def get_project_health(project: str, period: str = "3m") -> dict:
	"""Project Health dashboard data for one project (visibility rules apply)."""
	from auri_pms.permissions import can_see_project
	from auri_pms.tracking.health import get_health, health_visible

	if not frappe.db.exists("Project", project) or not can_see_project(project):
		frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
	from auri_pms.tracking.risk import risk_summary

	data = get_health(project, period)
	data["risks"] = risk_summary(project)
	if not health_visible(project, "hub"):
		data["status"] = None
	return data


# --------------------------------------------------------------------------- dashboards
@frappe.whitelist()
def get_portfolio(period: str = "3m") -> dict:
	"""Portfolio dashboard: health and delivery numbers of every project the user can see."""
	from auri_pms.tracking.dashboards import get_portfolio_data

	return get_portfolio_data(period)


@frappe.whitelist()
def get_my_work() -> dict:
	"""My Work dashboard for the current user."""
	from auri_pms.tracking.dashboards import get_my_work_data

	return get_my_work_data()


@frappe.whitelist()
def get_quality(project: str | None = None, period: str = "3m") -> dict:
	"""Quality dashboard for all visible projects or one project."""
	from auri_pms.permissions import can_see_project
	from auri_pms.tracking.dashboards import get_quality_data

	if project and (not frappe.db.exists("Project", project) or not can_see_project(project)):
		frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
	return get_quality_data(project or None, period)


@frappe.whitelist()
def get_status_report_html(project: str, from_date: str, to_date: str, note: str | None = None) -> dict:
	"""Preview of the client status report: its data summary and the HTML that would be emailed."""
	from auri_pms.tracking.status_report import build_report, default_subject, render_html

	report = build_report(project, from_date, to_date)
	return {
		"html": render_html(report, note),
		"subject": default_subject(report),
		"status": report.status,
		"recipients": frappe.db.get_value("Project", project, "tracker_report_recipients") or "",
		"can_send": bool(get_capabilities(project)["can_manage_releases"]),
	}


@frappe.whitelist()
def email_status_report(
	project: str,
	from_date: str,
	to_date: str,
	recipients: str,
	subject: str | None = None,
	note: str | None = None,
) -> str:
	"""Email the status report to ``recipients`` and log it; returns the Project Status Report name."""
	from auri_pms.tracking.status_report import send_report

	return send_report(project, from_date, to_date, recipients, subject, note)


@frappe.whitelist()
def status_report_pdf(project: str, from_date: str, to_date: str, note: str | None = None) -> None:
	"""Download the status report as a PDF."""
	from auri_pms.tracking.status_report import get_pdf_bytes

	frappe.local.response.filename = f"status-report-{project}-{from_date}-{to_date}.pdf"
	frappe.local.response.filecontent = get_pdf_bytes(project, from_date, to_date, note)
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def get_status_report_history(project: str) -> list[dict]:
	"""Recently sent status reports of a project."""
	return frappe.get_list(
		"Project Status Report",
		filters={"project": project},
		fields=["name", "subject", "from_date", "to_date", "sent_on", "sent_to", "status_level", "scheduled"],
		order_by="sent_on desc",
		limit_page_length=10,
	)
