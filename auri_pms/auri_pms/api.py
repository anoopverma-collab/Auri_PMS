"""Whitelisted API of Auri PMS (spec 5 R-18, section 6)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today

from auri_pms.auri_pms.utils import (
	get_capabilities,
	get_descendants,
	get_enabled_trackers,
	is_admin,
	nearest_indicator,
	transition_allowed,
)
from auri_pms.permissions import can_see_project


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
def status_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | str | None
):
	"""Link query for Work Item.status: the current status plus the allowed next statuses."""
	filters = frappe._dict(filters or {})
	if filters.work_item and frappe.db.exists("Work Item", filters.work_item):
		allowed = get_allowed_statuses(filters.work_item)
		allowed = [frappe.db.get_value("Work Item", filters.work_item, "status"), *allowed]
	else:
		allowed = get_allowed_statuses(None, {"tracker": filters.tracker, "project": filters.project})
	return [[s] for s in allowed if not txt or txt.lower() in s.lower()]


@frappe.whitelist()
def tracker_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | str | None
):
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
def assignee_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | str | None
):
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
def parent_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | str | None
):
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
def project_create_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | str | None
):
	"""Link query for Work Item.project: projects (with an identifier) the user may create items in."""
	candidates = frappe.get_list(
		"Project",
		filters={"pms_enabled": 1},
		or_filters={"name": ["like", _like(txt)], "project_name": ["like", _like(txt)]},
		fields=["name", "project_name"],
		order_by="modified desc",
		limit_page_length=200,
	)
	rows = [
		[p.name, p.project_name]
		for p in candidates
		if is_admin() or get_capabilities(p.name)["can_create_items"]
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
		filters={"pms_enabled": 1},
		fields=[
			"name",
			"project_name",
			"tracker_identifier",
			"status",
			"is_public",
			"expected_start_date",
			"expected_end_date",
		],
		order_by="modified desc",
		limit_page_length=0,
	)
	from auri_pms.permissions import can_see_project

	# an ERPNext Projects role sees every Project record, but the Project Hub shows only the projects the user is allocated to
	projects = [p for p in projects if can_see_project(p.name)]
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
			fields=["name", "sprint_name", "project", "percent_complete", "end_date"],
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
		project["closed"] = stats[project.name]["total"] - stats[project.name]["open"]
		project["members"] = members.get(project.name, 0)
		project["active_sprint"] = sprints.get(project.name)
	return projects


@frappe.whitelist()
def get_project_hub(project: str) -> dict:
	"""Everything the Project Hub shows for one project (visibility rules apply)."""
	from auri_pms.auri_pms.utils import get_burndown
	from auri_pms.permissions import can_see_project

	if not frappe.db.exists("Project", {"name": project, "pms_enabled": 1}) or not can_see_project(project):
		frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
	info = frappe.db.get_value(
		"Project",
		project,
		[
			"name",
			"project_name",
			"tracker_identifier",
			"status",
			"is_public",
			"expected_start_date",
			"expected_end_date",
			"pms_budget_hours",
		],
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
			"estimated_hours",
			"dependent_on_client",
			"client_dependency_note",
			"client_dependency_since",
			"creation",
			"closed_on",
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
		"hours_estimated": flt(sum(flt(i.estimated_hours) for i in items), 2),
		"hours_budget": flt(info.pms_budget_hours, 2),
	}
	# open tickets per person (overdue share included), busiest first
	load: dict[str, dict] = {}
	for i in open_items:
		if not i.assigned_to:
			continue
		row = load.setdefault(i.assigned_to, {"user": i.assigned_to, "open": 0, "overdue": 0})
		row["open"] += 1
		row["overdue"] += int(bool(i.due_date and getdate(i.due_date) < today_))
	names = {
		u.name: u.full_name
		for u in frappe.get_all(
			"User", filters={"name": ["in", list(load) or [""]]}, fields=["name", "full_name"]
		)
	}
	by_assignee = sorted(
		({**r, "name": names.get(r["user"]) or r["user"]} for r in load.values()),
		key=lambda r: (-r["open"], r["name"]),
	)

	from auri_pms.auri_pms.allocation import project_allocation
	from auri_pms.auri_pms.health import (
		count_by,
		count_by_module,
		created_resolved_closed,
		make_buckets,
		module_labels,
	)
	from auri_pms.auri_pms.risk import risk_summary

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
		fields=["user", "full_name", "project_role", "allocation_pct"],
		order_by="idx asc",
	)
	return frappe._dict(
		allocation=project_allocation(project, today_=today_),
		flow=created_resolved_closed(items, make_buckets("3m", None, today_)),
		project=info,
		capabilities=caps,
		numbers=numbers,
		by_status=count_by(open_items, "status", ordered_by_status=True),
		by_tracker=count_by(open_items, "tracker"),
		by_module=count_by_module(open_items, module_labels(project)),
		risks=risk_summary(project),
		by_priority=count_by(open_items, "priority"),
		by_assignee=by_assignee,
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
	from auri_pms.auri_pms.health import get_health, health_visible
	from auri_pms.permissions import can_see_project

	if not frappe.db.exists("Project", project) or not can_see_project(project):
		frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
	from auri_pms.auri_pms.allocation import project_team
	from auri_pms.auri_pms.dashboards import notes_summary, project_billing
	from auri_pms.auri_pms.risk import risk_summary
	from auri_pms.auri_pms.utils import portfolio_projects

	data = get_health(project, period)
	data["risks"] = risk_summary(project)
	data["billing"] = project_billing(project)
	data["notes"] = notes_summary(project)
	data["can_note"] = (
		project in portfolio_projects()
	)  # whoever sees the project on the Portfolio may keep notes on it
	data["team"] = project_team(project, portfolio_projects())
	if not health_visible(project, "hub"):
		data["status"] = None
	return data


# --------------------------------------------------------------------------- dashboards
@frappe.whitelist()
def get_project_periods(project: str, ranges: str | list) -> list[dict]:
	"""Tickets and billable time of one project for several periods: ``ranges`` is [{key, from_date, to_date}]."""
	from auri_pms.auri_pms.dashboards import project_period_counts
	from auri_pms.permissions import can_see_project

	if not frappe.db.exists("Project", project) or not can_see_project(project):
		frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
	return project_period_counts(project, frappe.parse_json(ranges) if isinstance(ranges, str) else ranges)


@frappe.whitelist()
def get_portfolio(period: str = "3m") -> dict:
	"""Portfolio dashboard: health and delivery numbers of every project the user can see."""
	from auri_pms.auri_pms.dashboards import get_portfolio_data

	return get_portfolio_data(period)


@frappe.whitelist()
def get_management_dashboard(project: str | None = None, release: str | None = None, sprint: str | None = None) -> dict:
	"""Delivery & Health: projects, releases, sprints, tasks, workload and delivery health in one payload,
	optionally narrowed to one or several projects (a name, comma-separated names or a JSON list), a release and a sprint."""
	from auri_pms.auri_pms.management import get_management_data

	return get_management_data(project or None, release or None, sprint or None)


@frappe.whitelist()
def get_portfolio_tickets(from_date: str | None = None, to_date: str | None = None) -> list[dict]:
	"""Tickets created, closed and in progress per Portfolio project for a period (all time without dates)."""
	from auri_pms.auri_pms.dashboards import get_portfolio_ticket_counts

	return get_portfolio_ticket_counts(from_date, to_date)


@frappe.whitelist()
def get_project_notes(project: str) -> list[dict]:
	"""The notes of a Portfolio project, newest first."""
	from auri_pms.auri_pms.dashboards import project_notes
	from auri_pms.auri_pms.utils import portfolio_projects

	if project not in portfolio_projects():
		frappe.throw(_("You cannot see the notes of Project {0}").format(project), frappe.PermissionError)
	return project_notes(project)


@frappe.whitelist(methods=["POST"])
def add_project_note(project: str, note: str) -> list[dict]:
	"""Add a note to a Portfolio project; returns the project's notes, newest first."""
	from auri_pms.auri_pms.dashboards import add_project_note as add

	return add(project, note)


@frappe.whitelist(methods=["POST"])
def delete_project_note(project: str, note: str) -> list[dict]:
	"""Delete a note of a Portfolio project (its author or an admin); returns the notes that are left."""
	from auri_pms.auri_pms.dashboards import delete_project_note as delete

	return delete(project, note)


@frappe.whitelist()
def get_my_work() -> dict:
	"""My Work dashboard for the current user."""
	from auri_pms.auri_pms.dashboards import get_my_work_data

	return get_my_work_data()


@frappe.whitelist()
def get_quality(project: str | None = None, period: str = "3m") -> dict:
	"""Quality dashboard for all visible projects or one project."""
	from auri_pms.auri_pms.dashboards import get_quality_data
	from auri_pms.permissions import can_see_project

	if project and (not frappe.db.exists("Project", project) or not can_see_project(project)):
		frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
	return get_quality_data(project or None, period)


def parse_excluded(exclude: str | list | None) -> list[str]:
	"""Ticket names the user removed from one report (a JSON list from the client)."""
	names = frappe.parse_json(exclude) if isinstance(exclude, str) else exclude
	return [str(n) for n in (names or []) if n][:500]


def parse_included(include: str | dict | list | None) -> dict[str, str]:
	"""Tickets added to one report with their note for the client (a JSON object name -> note)."""
	values = frappe.parse_json(include) if isinstance(include, str) else include
	if isinstance(values, list):
		values = dict.fromkeys(values, "")
	return {str(k): str(v or "")[:500] for k, v in list((values or {}).items())[:200] if k}


def parse_order(order: str | list | None) -> list[str]:
	"""Section keys in the order chosen for one report (a JSON list from the client); unknown keys are dropped."""
	from auri_pms.auri_pms.status_report import SECTION_LABELS

	values = frappe.parse_json(order) if isinstance(order, str) else order
	return [str(k) for k in (values or []) if k in SECTION_LABELS]


def parse_sections(sections: str | dict | None) -> dict[str, int]:
	"""Section switches chosen for one report (a JSON object from the client); unknown keys are ignored."""
	from auri_pms.auri_pms.status_report import REPORT_SECTIONS

	values = frappe.parse_json(sections) if isinstance(sections, str) else sections
	return {k: cint(v) for k, v in (values or {}).items() if k in REPORT_SECTIONS}


@frappe.whitelist()
def get_status_report_html(
	project: str,
	from_date: str,
	to_date: str,
	note: str | None = None,
	exclude: str | None = None,
	template: str | None = None,
	include: str | None = None,
	sections: str | None = None,
	order: str | None = None,
	ticket_notes: str | None = None,
) -> dict:
	"""Preview of the client status report: its data summary and the HTML that would be emailed."""
	from auri_pms.auri_pms.health import status_for_sections
	from auri_pms.auri_pms.status_report import (
		build_report,
		current_order,
		default_subject,
		merge_recipients,
		render_html,
		section_switches,
		visible_tickets,
	)

	report = build_report(
		project,
		from_date,
		to_date,
		parse_excluded(exclude),
		parse_included(include),
		parse_included(ticket_notes),
	)
	switches = section_switches(parse_sections(sections))
	chosen_order = parse_order(order)
	return {
		"html": render_html(report, note, template or None, parse_sections(sections), chosen_order),
		"order": current_order(template or None, chosen_order),
		"sections": switches,
		"tickets": visible_tickets(report.tickets, switches, current_order(template or None, chosen_order)),
		"added": [{"name": i.name, "subject": i.subject} for i in report.extra],
		"subject": default_subject(report, template or None),
		"default_template": frappe.db.get_single_value("PMS Settings", "report_email_template") or "",
		"status": status_for_sections(report.status, switches),
		"recipients": merge_recipients(
			frappe.db.get_value("Project", project, "tracker_report_recipients"),
			frappe.db.get_single_value("PMS Settings", "report_default_recipients"),
		),
		"cc": merge_recipients(
			frappe.db.get_value("Project", project, "tracker_report_cc"),
			frappe.db.get_single_value("PMS Settings", "report_default_cc"),
		),
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
	exclude: str | None = None,
	template: str | None = None,
	include: str | None = None,
	sections: str | None = None,
	order: str | None = None,
	ticket_notes: str | None = None,
	cc: str | None = None,
	attachments: str | None = None,
) -> str:
	"""Email the status report to ``recipients`` (with optional ``cc``) and log it; returns the Project Status Report name."""
	from auri_pms.auri_pms.status_report import send_report

	return send_report(
		project,
		from_date,
		to_date,
		recipients,
		subject,
		note,
		exclude=parse_excluded(exclude),
		template=template or None,
		include=parse_included(include),
		sections=parse_sections(sections),
		order=parse_order(order),
		cc=cc,
		ticket_notes=parse_included(ticket_notes),
		attachments=[str(n) for n in (frappe.parse_json(attachments) if attachments else [])],
	)


@frappe.whitelist()
def status_report_pdf(
	project: str,
	from_date: str,
	to_date: str,
	note: str | None = None,
	exclude: str | None = None,
	template: str | None = None,
	include: str | None = None,
	sections: str | None = None,
	order: str | None = None,
	ticket_notes: str | None = None,
) -> None:
	"""Download the status report as a PDF."""
	from auri_pms.auri_pms.status_report import get_pdf_bytes

	frappe.local.response.filename = f"status-report-{project}-{from_date}-{to_date}.pdf"
	frappe.local.response.filecontent = get_pdf_bytes(
		project,
		from_date,
		to_date,
		note,
		parse_excluded(exclude),
		template or None,
		parse_included(include),
		parse_sections(sections),
		parse_order(order),
		parse_included(ticket_notes),
	)
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
