"""Delivery & Health: one consolidated view of every project the user manages (the Portfolio's audience).

Everything is read through ``frappe.get_list`` so the visibility rules apply. Definitions, kept in one place:

* active project: ERPNext status Open; completed: Completed; delayed: Open with an overdue release, sprint or task.
* task: open = not closed; in progress = open with status In Progress; completed = closed and not Rejected;
  overdue = open with a due date before today.
* release: overdue = not Closed with a due date before today. Planned = its due date; actual = the day its last
  ticket was closed, once the release is Closed.
* sprint: open = not Completed; overdue = not Completed with an end date before today. A sprint belongs to the
  releases of the tickets in it (a Sprint has no release link of its own).
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from auri_pms.auri_pms.utils import portfolio_projects

UPCOMING_DAYS = 14
LIST_LIMIT = 15
NO_RELEASE = ""
ITEM_FIELDS = [
	"name",
	"subject",
	"project",
	"status",
	"is_closed",
	"assigned_to",
	"due_date",
	"release",
	"sprint",
	"estimated_hours",
	"spent_hours",
	"dependent_on_client",
	"closed_on",
]


def _pct(part: int, whole: int) -> int:
	return round(part * 100 / whole) if whole else 0


def _task_counts(items: list, today_) -> dict:
	"""Total, open, in progress, completed and overdue for a group of Work Items."""
	open_ = [i for i in items if not cint(i.is_closed)]
	completed = [i for i in items if cint(i.is_closed) and i.status != "Rejected"]
	return {
		"total": len(items),
		"open": len(open_),
		"in_progress": sum(1 for i in open_ if i.status == "In Progress"),
		"completed": len(completed),
		"overdue": sum(1 for i in open_ if i.due_date and getdate(i.due_date) < today_),
	}


def _date(value) -> str | None:
	return str(getdate(value)) if value else None


def as_project_list(project) -> list[str]:
	"""The projects asked for: a name, a comma-separated string, a JSON list or a list (empty: no narrowing)."""
	if not project:
		return []
	if isinstance(project, str):
		text = project.strip()
		if text.startswith("["):
			project = json.loads(text)
		else:
			project = [part for part in text.split(",")]
	return list(dict.fromkeys(str(p).strip() for p in project if str(p).strip()))


def get_management_data(
	project: str | list | None = None, release: str | None = None, sprint: str | None = None
) -> frappe._dict:
	"""The numbers of Delivery & Health (see the module docstring for the definitions).

	``project`` (one or several), ``release`` and ``sprint`` narrow every block. A release or sprint must belong to
	the selected project(s); ``options`` offers every project the user manages, but only the releases and sprints
	that were created for the selected ones."""
	allowed = portfolio_projects()
	if not allowed:
		frappe.throw(
			_("Delivery & Health is for Auri PMS Admins and for the managers of a project."),
			frappe.PermissionError,
		)
	today_ = getdate(today())
	soon = today_ + timedelta(days=UPCOMING_DAYS)
	selected = as_project_list(project)
	for name in selected:
		if name not in allowed:
			frappe.throw(_("{0} is not one of your projects").format(name), frappe.PermissionError)
	managed = frappe.get_list(
		"Project",
		filters={"pms_enabled": 1, "name": ["in", allowed]},
		fields=["name", "project_name", "tracker_identifier", "status"],
		order_by="project_name asc",
		limit_page_length=0,
	)
	for name in selected:
		if name not in {p.name for p in managed}:
			frappe.throw(_("{0} is not an Auri PMS project").format(name), frappe.ValidationError)
	projects = [p for p in managed if p.name in selected] if selected else managed
	names = [p.name for p in projects] or [""]
	items = frappe.get_list(
		"Work Item", filters={"project": ["in", names]}, fields=ITEM_FIELDS, limit_page_length=0
	)
	releases_all = frappe.get_list(
		"Release",
		filters={"project": ["in", names]},
		fields=["name", "release_name", "project", "status", "due_date", "percent_complete"],
		order_by="due_date asc",
		limit_page_length=0,
	)
	sprints_all = frappe.get_list(
		"Sprint",
		filters={"project": ["in", names]},
		fields=["name", "sprint_name", "project", "status", "start_date", "end_date", "percent_complete"],
		order_by="end_date asc",
		limit_page_length=0,
	)
	project_label = {p.name: p.project_name or p.name for p in projects}
	identifier = {p.name: p.tracker_identifier for p in projects}
	if release and release not in {r.name for r in releases_all}:
		frappe.throw(_("{0} is not a release of the selected project").format(release), frappe.ValidationError)
	if sprint and sprint not in {s.name for s in sprints_all}:
		frappe.throw(_("{0} is not a sprint of the selected project").format(sprint), frappe.ValidationError)
	options = {
		"projects": [{"name": p.name, "label": p.project_name or p.name} for p in managed],
		"releases": [
			{
				"name": r.name,
				"label": r.release_name or r.name,
				"project": r.project,
				"project_label": project_label.get(r.project, r.project),
			}
			for r in releases_all
		],
		"sprints": [
			{
				"name": s.name,
				"label": s.sprint_name or s.name,
				"project": s.project,
				"project_label": project_label.get(s.project, s.project),
			}
			for s in sprints_all
		],
	}
	if release:
		items = [i for i in items if i.release == release]
	if sprint:
		items = [i for i in items if i.sprint == sprint]

	by_project, by_release, by_sprint = defaultdict(list), defaultdict(list), defaultdict(list)
	sprint_releases: dict[str, set] = defaultdict(set)
	for item in items:
		by_project[item.project].append(item)
		by_release[item.release or NO_RELEASE].append(item)
		if item.sprint:
			by_sprint[item.sprint].append(item)
			sprint_releases[item.sprint].add(item.release or NO_RELEASE)

	# narrow the lists to what the filters leave: a release keeps the sprints that hold its tickets and the
	# other way round
	releases, sprints = releases_all, sprints_all
	if release:
		releases = [r for r in releases_all if r.name == release]
		sprints = [s for s in sprints_all if s.name in sprint_releases]
	if sprint:
		sprints = [s for s in sprints if s.name == sprint]
		if not release:
			releases = [r for r in releases_all if r.name in by_release]

	# ---- hours: estimated (on the tickets) against actual and billable (Time Entries), all time; a release or sprint
	# filter keeps the time logged on its tickets
	time_filters = {"project": ["in", names]}
	if release or sprint:
		time_filters["work_item"] = ["in", [i.name for i in items] or [""]]
	actual = {r.project: flt(r.hours) for r in frappe.get_list("Time Entry", filters=time_filters, fields=["project", {"SUM": "hours", "as": "hours"}], group_by="project", limit_page_length=0)}
	billable = {
		r.project: flt(r.hours)
		for r in frappe.get_list(
			"Time Entry",
			filters={**time_filters, "is_billable": 1},
			fields=["project", {"SUM": "hours", "as": "hours"}],
			group_by="project",
			limit_page_length=0,
		)
	}
	hour_rows = []
	for p in projects:
		est = sum(flt(i.estimated_hours) for i in by_project.get(p.name, []))
		act, bill = actual.get(p.name, 0.0), billable.get(p.name, 0.0)
		hour_rows.append(
			{
				"name": p.name,
				"label": p.project_name or p.name,
				"estimated": flt(est, 2),
				"actual": flt(act, 2),
				"billable": flt(bill, 2),
				"billable_pct": flt(bill * 100 / act, 1) if act else None,
				"variance": flt(act - est, 2),  # over (+) or under (-) the estimate
			}
		)
	hour_total = {k: flt(sum(r[k] for r in hour_rows), 2) for k in ("estimated", "actual", "billable")}
	hour_total["billable_pct"] = flt(hour_total["billable"] * 100 / hour_total["actual"], 1) if hour_total["actual"] else None
	hour_total["variance"] = flt(hour_total["actual"] - hour_total["estimated"], 2)

	# ---- releases: planned against actual
	release_rows = []
	for r in releases:
		counts = _task_counts(by_release.get(r.name, []), today_)
		closed = r.status == "Closed"
		closed_days = [getdate(i.closed_on) for i in by_release.get(r.name, []) if i.closed_on and cint(i.is_closed)]
		actual = max(closed_days) if closed and closed_days else None
		due = getdate(r.due_date) if r.due_date else None
		overdue = bool(due and not closed and due < today_)
		linked = [s for s in sprints if r.name in sprint_releases.get(s.name, ())]
		release_rows.append(
			{
				"name": r.name,
				"release_name": r.release_name or r.name,
				"project": r.project,
				"project_label": project_label.get(r.project, r.project),
				"status": r.status,
				"planned": _date(due),
				"actual": _date(actual),
				"late_days": (
					max(0, ((actual or today_) - due).days) if due and (closed or overdue) else 0
				),
				"late": overdue,
				"upcoming": bool(due and not closed and today_ <= due <= soon),
				"percent": flt(r.percent_complete),
				"sprints_total": len(linked),
				"sprints_open": sum(1 for s in linked if s.status != "Completed"),
				"sprints_overdue": sum(
					1 for s in linked if s.status != "Completed" and s.end_date and getdate(s.end_date) < today_
				),
				**counts,
			}
		)

	# ---- sprints: progress and overdue
	release_label = {r["name"]: r["release_name"] for r in release_rows}
	sprint_rows = []
	for s in sprints:
		end = getdate(s.end_date) if s.end_date else None
		overdue = bool(s.status != "Completed" and end and end < today_)
		sprint_rows.append(
			{
				"name": s.name,
				"sprint_name": s.sprint_name or s.name,
				"project": s.project,
				"project_label": project_label.get(s.project, s.project),
				"status": s.status,
				"start": _date(s.start_date),
				"end": _date(end),
				"percent": flt(s.percent_complete),
				"late": overdue,
				"releases": sorted(
					release_label.get(r, r) for r in sprint_releases.get(s.name, ()) if r != NO_RELEASE
				),
				**_task_counts(by_sprint.get(s.name, []), today_),
			}
		)

	# ---- people: assigned, pending and overdue per person (Assigned To and Additional Assignees)
	item_names = [i.name for i in items]
	extra = (
		frappe.get_all(
			"Work Item Assignee",
			filters={"parenttype": "Work Item", "parent": ["in", item_names]},
			fields=["parent", "user"],
			limit_page_length=0,
		)
		if item_names
		else []
	)
	by_name = {i.name: i for i in items}
	per_user: dict[str, list] = defaultdict(list)
	for item in items:
		per_user[item.assigned_to or ""].append(item)
	for row in extra:
		if row.user and row.user != by_name[row.parent].assigned_to:
			per_user[row.user].append(by_name[row.parent])
	full_names = {
		u.name: u.full_name or u.name
		for u in frappe.get_all(
			"User", filters={"name": ["in", [u for u in per_user if u] or [""]]}, fields=["name", "full_name"]
		)
	}
	users = []
	for user, rows in per_user.items():
		counts = _task_counts(rows, today_)
		open_rows = [i for i in rows if not cint(i.is_closed)]
		users.append(
			{
				"user": user,
				"full_name": full_names.get(user, user) if user else _("Unassigned"),
				"assigned": counts["total"],
				"pending": counts["open"],
				"in_progress": counts["in_progress"],
				"overdue": counts["overdue"],
				"completed": counts["completed"],
				"open_hours": round(sum(flt(i.estimated_hours) for i in open_rows), 1),
				"projects": len({i.project for i in rows}),
			}
		)
	users.sort(key=lambda u: (u["user"] == "", -u["pending"], -u["overdue"], u["full_name"]))

	# ---- projects: status, delayed and progress
	overdue_release = {r["project"] for r in release_rows if r["late"]}
	overdue_sprint = {s["project"] for s in sprint_rows if s["late"]}
	project_rows = []
	for p in projects:
		counts = _task_counts(by_project.get(p.name, []), today_)
		p_releases = [r for r in release_rows if r["project"] == p.name]
		p_sprints = [s for s in sprint_rows if s["project"] == p.name]
		reasons = []
		if p.name in overdue_release:
			reasons.append(_("overdue release"))
		if p.name in overdue_sprint:
			reasons.append(_("overdue sprint"))
		if counts["overdue"]:
			reasons.append(_("overdue tasks"))
		delayed = p.status == "Open" and bool(reasons)
		upcoming = sorted(r["planned"] for r in p_releases if r["status"] != "Closed" and r["planned"])
		active_sprint = next((s for s in p_sprints if s["status"] == "Active"), None)
		decided = counts["total"] - sum(1 for i in by_project.get(p.name, []) if i.status == "Rejected")
		project_rows.append(
			{
				"name": p.name,
				"project_name": project_label[p.name],
				"identifier": identifier[p.name],
				"status": p.status,
				"delayed": delayed,
				"delay_reasons": reasons if delayed else [],
				"progress": _pct(counts["completed"], decided),
				"releases": len(p_releases),
				"releases_closed": sum(1 for r in p_releases if r["status"] == "Closed"),
				"releases_overdue": sum(1 for r in p_releases if r["late"]),
				"sprints_open": sum(1 for s in p_sprints if s["status"] != "Completed"),
				"sprint_percent": active_sprint["percent"] if active_sprint else None,
				"next_due": upcoming[0] if upcoming else None,
				**counts,
			}
		)
	project_rows.sort(key=lambda r: (not r["delayed"], r["project_name"].lower()))

	# ---- delivery health
	open_items = [i for i in items if not cint(i.is_closed)]
	due_soon = sorted(
		(i for i in open_items if i.due_date and today_ <= getdate(i.due_date) <= soon),
		key=lambda i: (getdate(i.due_date), i.name),
	)
	pending = [i for i in open_items if not i.assigned_to or cint(i.dependent_on_client)]

	def task_row(i) -> dict:
		return {
			"name": i.name,
			"subject": i.subject,
			"project": i.project,
			"project_label": project_label.get(i.project, i.project),
			"assigned_to": full_names.get(i.assigned_to, i.assigned_to or ""),
			"due_date": _date(i.due_date),
			"waiting_on_client": bool(cint(i.dependent_on_client)),
		}

	delayed_releases = sorted((r for r in release_rows if r["late"]), key=lambda r: -r["late_days"])
	upcoming_releases = [r for r in release_rows if r["upcoming"]]
	upcoming_sprints = [
		s for s in sprint_rows if s["status"] != "Completed" and s["end"] and today_ <= getdate(s["end"]) <= soon
	]
	completed_projects = sum(1 for p in projects if p.status == "Completed")
	all_counts = _task_counts(items, today_)
	return frappe._dict(
		today=str(today_),
		upcoming_days=UPCOMING_DAYS,
		filters={
			"projects": selected,
			"project": selected[0] if len(selected) == 1 else "",  # kept for callers that send one project
			"release": release or "",
			"sprint": sprint or "",
		},
		options=options,
		kpis={
			"projects": len(projects),
			"active": sum(1 for p in projects if p.status == "Open"),
			"completed": completed_projects,
			"cancelled": sum(1 for p in projects if p.status == "Cancelled"),
			"delayed": sum(1 for p in project_rows if p["delayed"]),
			"releases": len(release_rows),
			"releases_open": sum(1 for r in release_rows if r["status"] != "Closed"),
			"releases_overdue": len(delayed_releases),
			"sprints": len(sprint_rows),
			"sprints_open": sum(1 for s in sprint_rows if s["status"] != "Completed"),
			"sprints_overdue": sum(1 for s in sprint_rows if s["late"]),
			"pending_activities": len(pending),
			"unassigned": sum(1 for i in open_items if not i.assigned_to),
			"waiting_on_client": sum(1 for i in open_items if cint(i.dependent_on_client)),
			**{f"tasks_{k}": v for k, v in all_counts.items()},
		},
		projects=project_rows,
		releases=release_rows,
		sprints=sprint_rows,
		no_release=_task_counts(by_release.get(NO_RELEASE, []), today_),
		users=users,
		upcoming={
			"releases": upcoming_releases[:LIST_LIMIT],
			"sprints": upcoming_sprints[:LIST_LIMIT],
			"tasks": [task_row(i) for i in due_soon[:LIST_LIMIT]],
		},
		hours={"projects": hour_rows, "total": hour_total},
		delayed_releases=delayed_releases[:LIST_LIMIT],
		pending=[task_row(i) for i in pending[:LIST_LIMIT]],
		# every record behind a delivery-health tile, so the tile opens a list with exactly its count
		ids={
			"delayed_projects": [p["name"] for p in project_rows if p["delayed"]],
			"delayed_releases": [r["name"] for r in delayed_releases],
			"overdue_sprints": [s["name"] for s in sprint_rows if s["late"]],
			"pending": [i.name for i in pending],
		},
	)
