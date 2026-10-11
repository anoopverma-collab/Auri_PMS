"""Data for the Portfolio, My Work and Quality dashboards (all reads are permission aware)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from auri_pms.auri_pms.health import (
	AGE_BUCKETS,
	PERIODS,
	as_date,
	count_by,
	deep_dict,
	make_buckets,
	monday,
	overall_status,
	ticket_flow,
	time_summary,
)
from auri_pms.auri_pms.risk import my_risks, portfolio_risk_counts
from auri_pms.auri_pms.utils import get_settings

LEVEL_ORDER = {"red": 0, "amber": 1, "green": 2, "none": 3}
CRITICAL_PRIORITIES = ("Urgent", "Immediate")
WORK_ITEM_FIELDS = [
	"name",
	"subject",
	"project",
	"tracker",
	"status",
	"priority",
	"assigned_to",
	"due_date",
	"is_closed",
	"creation",
	"closed_on",
	"estimated_hours",
	"spent_hours",
	"done_percent",
	"sprint",
	"category",
	"project_module",
	"dependent_on_client",
	"client_dependency_since",
]


def full_names(users: list[str]) -> dict[str, str]:
	"""{user: full name} for ``users`` (falls back to the user id)."""
	rows = frappe.get_all(
		"User", filters={"name": ["in", [u for u in users if u] or [""]]}, fields=["name", "full_name"]
	)
	return {r.name: r.full_name or r.name for r in rows}


# --------------------------------------------------------------------------- portfolio
def get_portfolio_data(period: str = "3m") -> frappe._dict:
	"""One row of health and delivery numbers per visible project, plus portfolio totals and series."""
	period = period if period in PERIODS else "3m"
	today_ = getdate(today())
	projects = frappe.get_list(
		"Project",
		filters={"tracker_identifier": ["is", "set"]},
		fields=["name", "project_name", "tracker_identifier", "status", "is_public"],
		order_by="modified desc",
		limit_page_length=200,
	)
	names = [p.name for p in projects]
	items = frappe.get_list(
		"Work Item",
		filters={"project": ["in", names or [""]]},
		fields=[*WORK_ITEM_FIELDS, "modified"],
		limit_page_length=0,
	)
	entries = frappe.get_list(
		"Time Entry",
		filters={"project": ["in", names or [""]]},
		fields=["project", "date", "hours", "is_billable", "user", "activity_type"],
		limit_page_length=0,
	)
	earliest = min([as_date(i.creation) for i in items] + [as_date(e.date) for e in entries] or [today_])
	buckets = make_buckets(period, earliest, today_)
	items_by, entries_by = defaultdict(list), defaultdict(list)
	for item in items:
		items_by[item.project].append(item)
	for entry in entries:
		entries_by[entry.project].append(entry)
	show_status = {
		p.name: cint(p.show_health_portfolio)
		for p in frappe.get_all(
			"Project", filters={"name": ["in", names or [""]]}, fields=["name", "show_health_portfolio"]
		)
	}
	sprints = {
		s.project: s
		for s in frappe.get_list(
			"Sprint",
			filters={"project": ["in", names or [""]], "status": "Active"},
			fields=["name", "sprint_name", "project", "percent_complete", "end_date"],
			limit_page_length=0,
		)
	}

	risk_counts = portfolio_risk_counts([p.name for p in projects])
	rows = []
	series = {
		k: [0] * len(buckets.starts)
		for k in ("created", "resolved", "open_trend", "billable", "non_billable")
	}
	for project in projects:
		p_items, p_entries = items_by.get(project.name, []), entries_by.get(project.name, [])
		flow = ticket_flow(p_items, buckets)
		time = time_summary(p_entries, p_items, buckets)
		status = overall_status(project.name, flow, time, today_)
		for key, source in (
			("created", flow["created"]),
			("resolved", flow["resolved"]),
			("open_trend", flow["open_trend"]),
			("billable", time["billable_by_week"]),
			("non_billable", time["non_billable_by_week"]),
		):
			series[key] = [a + b for a, b in zip(series[key], source, strict=True)]
		reasons = [r for r in status["reasons"] if r["level"] in ("red", "amber")]
		hidden = not show_status.get(project.name)
		all_reasons = [] if hidden else [{"level": r["level"], "text": r["text"]} for r in status["reasons"]]
		if hidden:
			# the project owner chose not to show the health status here: the numbers stay, the verdict does not
			status = {"level": "none", "label": _("Hidden"), "score": None}
			reasons = []
		activity = [as_date(i.modified) for i in p_items] + [as_date(e.date) for e in p_entries]
		sprint = sprints.get(project.name)
		rows.append(
			{
				"name": project.name,
				"project_name": project.project_name or project.name,
				"identifier": project.tracker_identifier,
				"level": status["level"],
				"health_hidden": hidden,
				"label": status["label"],
				"score": status["score"],
				"headline": reasons[0]["text"] if reasons else "",
				"reasons": len(reasons),
				"reason_list": all_reasons,
				"open": flow["open"],
				"closed": flow["closed"],
				"total": flow["total"],
				"completion_pct": flow["completion_pct"],
				"overdue": flow["overdue"],
				"overdue_pct": flow["overdue_pct"],
				"client_dependent": flow["client_dependent"],
				"risks_open": risk_counts[project.name]["open"],
				"risks_critical": risk_counts[project.name]["critical"],
				"risks_high": risk_counts[project.name]["high"],
				"risks_overdue": risk_counts[project.name]["overdue"],
				"avg_resolution_days": flow["avg_resolution_days"],
				"created_period": sum(flow["created"]),
				"resolved_period": sum(flow["resolved"]),
				"hours_spent": time["spent"],
				"hours_period": flt(sum(time["billable_by_week"]) + sum(time["non_billable_by_week"]), 2),
				"billable_pct": time["billable_pct"],
				"estimated": time["estimated"],
				"burn_pct": time["burn_pct"],
				"sprint": {
					"name": sprint.name,
					"label": sprint.sprint_name,
					"percent": flt(sprint.percent_complete),
				}
				if sprint
				else None,
				"last_activity": str(max(activity)) if activity else None,
			}
		)
	rows.sort(
		key=lambda r: (
			LEVEL_ORDER[r["level"]],
			r["score"] if r["score"] is not None else 101,
			r["project_name"],
		)
	)

	spent = sum(r["hours_spent"] for r in rows)
	billable = sum(flt(r["hours_spent"]) * flt(r["billable_pct"]) / 100 for r in rows)
	estimated = sum(r["estimated"] for r in rows)
	kpis = {
		"projects": len(rows),
		"red": sum(r["level"] == "red" for r in rows),
		"amber": sum(r["level"] == "amber" for r in rows),
		"green": sum(r["level"] == "green" for r in rows),
		"none": sum(r["level"] == "none" and not r["health_hidden"] for r in rows),
		"risks_open": sum(r["risks_open"] for r in rows),
		"risks_critical": sum(r["risks_critical"] for r in rows),
		"risks_high": sum(r["risks_high"] for r in rows),
		"hidden": sum(r["health_hidden"] for r in rows),
		"open": sum(r["open"] for r in rows),
		"closed": sum(r["closed"] for r in rows),
		"overdue": sum(r["overdue"] for r in rows),
		"client_dependent": sum(r["client_dependent"] for r in rows),
		"hours_spent": flt(spent, 2),
		"hours_period": flt(sum(r["hours_period"] for r in rows), 2),
		"billable_pct": flt(billable * 100 / spent, 1) if spent else 0.0,
		"burn_pct": flt(spent * 100 / estimated, 1) if estimated else None,
		"avg_score": flt(
			sum(r["score"] for r in rows if r["score"] is not None)
			/ max(1, sum(r["score"] is not None for r in rows)),
			0,
		),
	}
	return deep_dict(
		{
			"period": period,
			"range_start": str(buckets.first_day),
			"bucket": buckets.kind,
			"labels": buckets.labels(),
			"kpis": kpis,
			"series": series,
			"projects": rows,
		}
	)


# --------------------------------------------------------------------------- my work
def get_my_work_data(user: str | None = None) -> frappe._dict:
	"""Everything assigned to (or raised by) the user, their hours this week and their active sprints."""
	user = user or frappe.session.user
	today_ = getdate(today())
	week_start = monday(today_)
	week_end = week_start + timedelta(days=6)
	items = frappe.get_list(
		"Work Item",
		filters={"assigned_to": user, "is_closed": 0},
		fields=[
			"name",
			"subject",
			"project",
			"tracker",
			"status",
			"priority",
			"due_date",
			"sprint",
			"project_module",
			"estimated_hours",
			"spent_hours",
			"done_percent",
			"dependent_on_client",
			"client_dependency_note",
			"client_dependency_since",
		],
		limit_page_length=0,
	)
	module_names = {
		m.name: m.module_name
		for m in frappe.get_all(
			"Project Module",
			filters={"name": ["in", list({i.project_module for i in items if i.project_module}) or [""]]},
			fields=["name", "module_name"],
		)
	}
	project_names = {
		p.name: p
		for p in frappe.get_all(
			"Project",
			filters={"name": ["in", list({i.project for i in items}) or [""]]},
			fields=["name", "project_name", "tracker_identifier"],
		)
	}
	blockers = blocked_by_open(items)
	groups: dict[str, list] = {"overdue": [], "today": [], "week": [], "later": [], "no_due": []}
	for item in sorted(items, key=lambda i: (i.due_date is None, str(i.due_date or ""), i.name)):
		due = getdate(item.due_date) if item.due_date else None
		row = {
			**item,
			"project_label": project_names[item.project].project_name or item.project
			if item.project in project_names
			else item.project,
			"module": module_names.get(item.project_module) or "",
			"blocked_by": blockers.get(item.name, []),
			"days_overdue": (today_ - due).days if due and due < today_ else 0,
		}
		key = (
			"no_due"
			if not due
			else "overdue"
			if due < today_
			else "today"
			if due == today_
			else "week"
			if due <= week_end
			else "later"
		)
		groups[key].append(row)

	raised = frappe.get_list(
		"Work Item",
		filters={"author": user, "is_closed": 0, "assigned_to": ["!=", user]},
		fields=["name", "subject", "project", "status", "assigned_to", "due_date", "priority"],
		order_by="modified desc",
		limit_page_length=10,
	)
	names = full_names([r.assigned_to for r in raised])
	for row in raised:
		row["assignee_name"] = (
			names.get(row.assigned_to, _("Unassigned")) if row.assigned_to else _("Unassigned")
		)

	capacity = flt(get_settings().get("weekly_capacity_hours")) or 40.0
	entries = frappe.get_list(
		"Time Entry",
		filters={"user": user, "date": ["between", [week_start, week_end]]},
		fields=["date", "hours", "is_billable"],
		limit_page_length=0,
	)
	billable_days, other_days = [0.0] * 7, [0.0] * 7
	for entry in entries:
		(billable_days if cint(entry.is_billable) else other_days)[
			(as_date(entry.date) - week_start).days
		] += flt(entry.hours)
	logged = sum(billable_days) + sum(other_days)
	missing = [
		(week_start + timedelta(days=n)).strftime("%a")
		for n in range(5)
		if week_start + timedelta(days=n) < today_ and billable_days[n] + other_days[n] == 0
	]

	closed = frappe.get_list(
		"Work Item",
		filters={"closed_by": user, "is_closed": 1, "closed_on": [">=", today_ - timedelta(days=27)]},
		fields=["name", "subject", "project", "closed_on"],
		order_by="closed_on desc",
		limit_page_length=0,
	)
	closed_weekly = [0, 0, 0, 0]
	for row in closed:
		index = 3 - min(3, (today_ - as_date(row.closed_on)).days // 7)
		closed_weekly[index] += 1

	return deep_dict(
		{
			"user": user,
			"today": str(today_),
			"week_start": str(week_start),
			"groups": groups,
			"tiles": {
				"open": len(items),
				"overdue": len(groups["overdue"]),
				"today": len(groups["today"]),
				"week": len(groups["week"]),
				"blocked": sum(1 for i in items if blockers.get(i.name)),
				"client_waiting": sum(1 for i in items if cint(i.dependent_on_client)),
				"hours_week": flt(logged, 2),
				"capacity": flt(capacity, 2),
				"capacity_pct": flt(logged * 100 / capacity, 0) if capacity else 0,
				"closed_28d": len(closed),
			},
			"hours": {
				"days": [(week_start + timedelta(days=n)).strftime("%a") for n in range(7)],
				"billable": [flt(v, 2) for v in billable_days],
				"non_billable": [flt(v, 2) for v in other_days],
				"missing_days": missing,
			},
			"raised": raised,
			"risks": my_risks(user),
			"sprints": my_sprints(user),
			"closed_weekly": closed_weekly,
			"closed_recent": closed[:5],
		}
	)


def blocked_by_open(items: list) -> dict[str, list[str]]:
	"""{item: [open items it is blocked by]} for the given items."""
	names = [i.name for i in items]
	if not names:
		return {}
	rows = frappe.get_all(
		"Work Item Relation",
		filters={"parent": ["in", names], "parenttype": "Work Item", "relation_type": "Blocked by"},
		fields=["parent", "related_work_item"],
	)
	open_targets = set(
		frappe.get_all(
			"Work Item",
			filters={"name": ["in", [r.related_work_item for r in rows] or [""]], "is_closed": 0},
			pluck="name",
		)
	)
	result: dict[str, list[str]] = defaultdict(list)
	for row in rows:
		if row.related_work_item in open_targets:
			result[row.parent].append(row.related_work_item)
	return result


def my_sprints(user: str) -> list[dict]:
	"""Active sprints in which the user has tickets, with their open/closed share."""
	sprints = frappe.get_list(
		"Sprint",
		filters={"status": "Active"},
		fields=[
			"name",
			"sprint_name",
			"project",
			"end_date",
			"percent_complete",
			"total_items",
			"closed_items",
		],
		limit_page_length=0,
	)
	if not sprints:
		return []
	mine = frappe.get_all(
		"Work Item",
		filters={"sprint": ["in", [s.name for s in sprints]], "assigned_to": user},
		fields=["sprint", "is_closed"],
	)
	today_ = getdate(today())
	result = []
	for sprint in sprints:
		own = [m for m in mine if m.sprint == sprint.name]
		if not own:
			continue
		result.append(
			{
				"name": sprint.name,
				"label": sprint.sprint_name,
				"project": sprint.project,
				"days_left": max((getdate(sprint.end_date) - today_).days, 0),
				"percent": flt(sprint.percent_complete),
				"mine_total": len(own),
				"mine_closed": sum(1 for m in own if cint(m.is_closed)),
			}
		)
	return result


# --------------------------------------------------------------------------- quality
def get_quality_data(project: str | None = None, period: str = "3m") -> frappe._dict:
	"""Defect flow, fix time, reopen rate and risks for the visible projects (or one project)."""
	period = period if period in PERIODS else "3m"
	today_ = getdate(today())
	defect_trackers = frappe.get_all("Ticket Type", filters={"is_defect": 1}, pluck="name")
	empty = {"period": period, "defect_trackers": defect_trackers, "has_data": False}
	if not defect_trackers:
		return deep_dict(empty)
	filters = {"project": project} if project else {}
	everything = frappe.get_list("Work Item", filters=filters, fields=WORK_ITEM_FIELDS, limit_page_length=0)
	bugs = [i for i in everything if i.tracker in defect_trackers]
	entries = frappe.get_list(
		"Time Entry", filters=filters, fields=["date", "hours", "project"], limit_page_length=0
	)
	earliest = min([as_date(i.creation) for i in everything] + [as_date(e.date) for e in entries] or [today_])
	buckets = make_buckets(period, earliest, today_)
	start = buckets.first_day
	flow = ticket_flow(bugs, buckets)
	open_bugs = [b for b in bugs if not cint(b.is_closed)]
	closed_bugs = [b for b in bugs if cint(b.is_closed)]

	opened_period = [b for b in bugs if as_date(b.creation) >= start]
	all_created_period = [i for i in everything if as_date(i.creation) >= start]
	fixed_period = [b for b in closed_bugs if b.closed_on and as_date(b.closed_on) >= start]
	hours_period = sum(flt(e.hours) for e in entries if as_date(e.date) >= start)

	fix_days: dict[str, list[int]] = defaultdict(list)
	for bug in fixed_period:
		fix_days[bug.priority].append((as_date(bug.closed_on) - as_date(bug.creation)).days)
	all_days = [d for days in fix_days.values() for d in days]

	reopen = reopen_stats(bugs, buckets)
	categories = category_names([b.category for b in bugs if b.category])
	by_category: dict[str, list[int]] = defaultdict(lambda: [0, 0])
	for bug in bugs:
		by_category[categories.get(bug.category, _("(none)")) if bug.category else _("(none)")][
			1 if cint(bug.is_closed) else 0
		] += 1

	by_module: dict[str, list[int]] = defaultdict(lambda: [0, 0])
	if any(b.project_module for b in bugs):
		module_rows = frappe.get_all(
			"Project Module",
			filters={"name": ["in", list({b.project_module for b in bugs if b.project_module})]},
			fields=["name", "module_name", "project"],
		)
		prefix = {m.name: m.module_name if project else f"{m.module_name} ({m.project})" for m in module_rows}
		for bug in bugs:
			by_module[
				prefix.get(bug.project_module, _("(no module)")) if bug.project_module else _("(no module)")
			][1 if cint(bug.is_closed) else 0] += 1
	else:
		for bug in bugs:
			by_module[_("(no module)")][1 if cint(bug.is_closed) else 0] += 1

	by_project = []
	if not project:
		labels = {
			p.name: p.project_name or p.name
			for p in frappe.get_all(
				"Project",
				filters={"name": ["in", list({i.project for i in everything}) or [""]]},
				fields=["name", "project_name"],
			)
		}
		grouped: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
		for item in everything:
			if as_date(item.creation) >= start:
				grouped[item.project][2] += 1
		for bug in bugs:
			grouped[bug.project][1 if cint(bug.is_closed) else 0] += 1
		by_project = sorted(
			[
				{
					"project": k,
					"label": labels.get(k, k),
					"open": v[0],
					"closed": v[1],
					"created_period": v[2],
				}
				for k, v in grouped.items()
			],
			key=lambda r: -r["open"],
		)[:12]

	critical_open = sorted(
		[b for b in open_bugs if b.priority in CRITICAL_PRIORITIES], key=lambda b: str(b.creation)
	)
	names = full_names([b.assigned_to for b in critical_open])
	ages: dict[str, list[int]] = defaultdict(lambda: [0, 0])
	for bug in open_bugs:
		age = (today_ - as_date(bug.creation)).days
		bucket = next(text for limit, text in AGE_BUCKETS if age <= limit)
		ages[bucket][0] += 1
		ages[bucket][1] += cint(bug.dependent_on_client)

	recent_28 = today_ - timedelta(days=28)
	opened_4w = sum(1 for b in bugs if as_date(b.creation) > recent_28)
	fixed_4w = sum(1 for b in closed_bugs if b.closed_on and as_date(b.closed_on) > recent_28)
	status = quality_status(
		critical_open, reopen, opened_4w, fixed_4w, today_, len(opened_period), hours_period
	)
	return deep_dict(
		{
			"has_data": bool(bugs),
			"period": period,
			"range_start": str(buckets.first_day),
			"bucket": buckets.kind,
			"labels": buckets.labels(),
			"defect_trackers": defect_trackers,
			"status": status,
			"tiles": {
				"open": len(open_bugs),
				"client_open": sum(1 for b in open_bugs if cint(b.dependent_on_client)),
				"closed": len(closed_bugs),
				"critical_open": len(critical_open),
				"opened_period": len(opened_period),
				"fixed_period": len(fixed_period),
				"avg_fix_days": flt(sum(all_days) / len(all_days), 1) if all_days else None,
				"bug_share_pct": flt(len(opened_period) * 100 / len(all_created_period), 1)
				if all_created_period
				else 0.0,
				"density": flt(len(opened_period) * 100 / hours_period, 1) if hours_period else None,
				"reopen_rate": reopen["rate"],
				"reopened": reopen["reopened"],
				"reopened_names": reopen["names"],
			},
			"flow": {
				"opened": flow["created"],
				"fixed": flow["resolved"],
				"open_trend": flow["open_trend"],
				"reopened": reopen["by_bucket"],
			},
			"open_by_priority": count_by(open_bugs, "priority"),
			"fix_time": [
				{"priority": k, "days": flt(sum(v) / len(v), 1), "count": len(v)}
				for k, v in sorted(fix_days.items(), key=lambda kv: -len(kv[1]))
			],
			"aging": [
				{"label": text, "count": ages[text][0], "client": ages[text][1]}
				if text in ages
				else {"label": text, "count": 0, "client": 0}
				for _limit, text in AGE_BUCKETS
			],
			"by_category": sorted(
				[{"label": k, "open": v[0], "closed": v[1]} for k, v in by_category.items()],
				key=lambda r: -(r["open"] + r["closed"]),
			)[:8],
			"by_module": sorted(
				[{"label": k, "open": v[0], "closed": v[1]} for k, v in by_module.items()],
				key=lambda r: (r["label"] == _("(no module)"), -(r["open"] + r["closed"]), r["label"]),
			)[:8],
			"by_project": by_project,
			"critical": [
				{
					"name": b.name,
					"subject": b.subject,
					"project": b.project,
					"priority": b.priority,
					"status": b.status,
					"client": cint(b.dependent_on_client),
					"age_days": (today_ - as_date(b.creation)).days,
					"assignee": names.get(b.assigned_to, _("Unassigned"))
					if b.assigned_to
					else _("Unassigned"),
				}
				for b in critical_open[:10]
			],
		}
	)


def category_names(categories: list[str]) -> dict[str, str]:
	"""{category id: display name}."""
	rows = frappe.get_all(
		"Work Item Category",
		filters={"name": ["in", list(set(categories)) or [""]]},
		fields=["name", "category_name"],
	)
	return {r.name: r.category_name for r in rows}


def reopen_stats(bugs: list, buckets) -> dict:
	"""Reopened bugs (status moved from a closed to an open status) from Frappe's change history."""
	closed_statuses = set(frappe.get_all("Work Item Status", filters={"is_closed": 1}, pluck="name"))
	names = [b.name for b in bugs]
	reopened: set[str] = set()
	by_bucket: dict[date, int] = defaultdict(int)
	for chunk_start in range(0, len(names), 500):
		rows = frappe.get_all(
			"Version",
			filters={"ref_doctype": "Work Item", "docname": ["in", names[chunk_start : chunk_start + 500]]},
			fields=["docname", "data", "creation"],
		)
		for row in rows:
			try:
				changes = json.loads(row.data or "{}").get("changed", [])
			except ValueError:
				continue
			if any(
				c[0] == "status" and c[1] in closed_statuses and c[2] not in closed_statuses for c in changes
			):
				reopened.add(row.docname)
				by_bucket[buckets.key(as_date(row.creation))] += 1
	ever_closed = {b.name for b in bugs if cint(b.is_closed)} | reopened
	return {
		"reopened": len(reopened),
		"names": sorted(reopened),
		"ever_closed": len(ever_closed),
		"rate": flt(len(reopened) * 100 / len(ever_closed), 1) if ever_closed else 0.0,
		"by_bucket": [by_bucket.get(s, 0) for s in buckets.starts],
	}


def quality_status(
	critical_open: list,
	reopen: dict,
	opened_4w: int,
	fixed_4w: int,
	today_: date,
	opened_period: int,
	hours: float,
) -> dict:
	"""Traffic light for quality with the reasons behind it."""
	reasons: list[dict] = []

	def add(level: str, text: str) -> None:
		reasons.append({"level": level, "text": text})

	stale = [b for b in critical_open if (today_ - as_date(b.creation)).days > 7]
	if stale:
		add("red", _("{0} critical bugs have been open for more than a week").format(len(stale)))
	elif critical_open:
		add("amber", _("{0} critical bugs are open").format(len(critical_open)))
	if reopen["ever_closed"] >= 5:
		if reopen["rate"] > 30:
			add("red", _("{0}% of fixed bugs were reopened").format(reopen["rate"]))
		elif reopen["rate"] > 15:
			add("amber", _("{0}% of fixed bugs were reopened").format(reopen["rate"]))
	if opened_4w >= 4 and opened_4w > fixed_4w * 1.5:
		add("amber", _("More bugs were opened than fixed over the last 4 weeks"))
	if hours and opened_period * 100 / hours > 5:
		add(
			"amber",
			_("High defect density: {0} bugs per 100 hours").format(flt(opened_period * 100 / hours, 1)),
		)
	level = "red" if any(r["level"] == "red" for r in reasons) else "amber" if reasons else "green"
	score = max(
		0,
		100
		- 25 * sum(r["level"] == "red" for r in reasons)
		- 10 * sum(r["level"] == "amber" for r in reasons),
	)
	if level == "green":
		add("green", _("No critical or reopened-bug risks detected"))
	return {
		"level": level,
		"label": {"green": _("Healthy"), "amber": _("Needs attention"), "red": _("At Risk")}[level],
		"score": score,
		"reasons": reasons,
	}
