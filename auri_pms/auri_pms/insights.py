# Copyright (c) 2026, Anoop Verma and contributors
# For license information, please see license.txt

"""Insights: ready-made analytical dashboards (delivery, workload, releases, quality, client, time) on Auri PMS data.

Every report returns the same shape so one renderer draws them all:
``{title, subtitle, kpis: [...], visuals: [...]}``. A visual is ``{title, kind, ...}`` where kind is
``line``, ``bar``, ``donut``, ``stack`` or ``table``.
"""

from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from auri_pms.auri_pms.health import make_buckets
from auri_pms.permissions import can_see_project

REPORTS = {
	"delivery": {
		"title": "Delivery Analysis",
		"about": "How much work arrives, how fast it is closed, and where it piles up.",
		"icon": "truck",
	},
	"workload": {
		"title": "Team Workload",
		"about": "Open, overdue and estimated work per person, and who is closing the most.",
		"icon": "users",
	},
	"releases": {
		"title": "Releases and Sprints",
		"about": "Progress of every release, what is due next and how much each sprint delivers.",
		"icon": "package",
	},
	"quality": {
		"title": "Quality Analysis",
		"about": "Bugs opened against fixed, time to fix, critical bugs and the oldest open ones.",
		"icon": "bug",
	},
	"client": {
		"title": "Client Dependency",
		"about": "Work that is blocked until the client answers, how long it has waited and where.",
		"icon": "clock",
	},
	"time": {
		"title": "Time and Billing",
		"about": "Hours logged, billable share, and where the time goes by person, activity and project.",
		"icon": "timer",
	},
}

AGE_BUCKETS = [("0-7 d", 0, 7), ("8-14 d", 8, 14), ("15-30 d", 15, 30), ("31-60 d", 31, 60), ("60+ d", 61, 10**6)]
ITEM_SQL = """select name, subject, project, tracker, status, priority, assigned_to, project_module, `release`, sprint,
	is_closed, date(creation) as created, closed_on, due_date, estimated_hours, spent_hours, done_percent,
	dependent_on_client, client_dependency_since from `tabWork Item` where project in %(projects)s"""


@frappe.whitelist()
def get_reports() -> list[dict]:
	"""The catalogue shown on the gallery page."""
	return [{"key": key, **{k: _(v) if k != "icon" else v for k, v in meta.items()}} for key, meta in REPORTS.items()]


@frappe.whitelist()
def get_insight(report: str, project: str | None = None, period: str = "3m") -> dict:
	"""One report for all projects the user sees, or for one project."""
	if report not in REPORTS:
		frappe.throw(_("Unknown report {0}").format(report))
	projects = visible_projects(project)
	ctx = Context(projects, period)
	data = globals()[f"report_{report}"](ctx)
	data.setdefault("title", _(REPORTS[report]["title"]))
	data["subtitle"] = _("{0} · {1}").format(
		project or _("1 project") if len(projects) == 1 else _("{0} projects").format(len(projects)), PERIOD_NOTE[ctx.period]
	)
	data["period"] = ctx.period
	return data


PERIOD_NOTE = {"1m": _("last month"), "3m": _("last 3 months"), "6m": _("last 6 months"), "all": _("overall")}


def visible_projects(project: str | None) -> list[str]:
	if project:
		if not frappe.db.exists("Project", project) or not can_see_project(project):
			frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
		return [project]
	enabled = frappe.get_all("Project", filters={"pms_enabled": 1}, pluck="name", order_by="name")
	return [p for p in enabled if can_see_project(p)]


class Context:
	"""The items, buckets and helpers every report shares."""

	def __init__(self, projects: list[str], period: str):
		self.projects = projects
		self.period = period if period in PERIOD_NOTE else "3m"
		self.today = getdate(today())
		self.items = (
			frappe.db.sql(ITEM_SQL, {"projects": projects}, as_dict=True) if projects else []
		)
		earliest = min((i.created for i in self.items), default=None)
		self.buckets = make_buckets(self.period, earliest, self.today)
		self.start = self.buckets.first_day
		self.names = {
			p.name: p.project_name or p.name
			for p in frappe.get_all("Project", filters={"name": ["in", projects or [""]]}, fields=["name", "project_name"])
		}
		self.users = {}

	def user(self, email: str | None) -> str:
		if not email:
			return _("Unassigned")
		if email not in self.users:
			self.users[email] = frappe.db.get_value("User", email, "full_name") or email
		return self.users[email]

	def module(self, item) -> str:
		"""Module name without its project prefix (``PROJ-0035-Stocks`` -> ``Stocks``)."""
		name = item.project_module or ""
		return name.removeprefix(f"{item.project}-") if name else _("(no module)")

	def bucket(self, day) -> int | None:
		"""Index of the bucket that holds `day`, or None when it is before the first one."""
		if not day:
			return None
		i = bisect_right(self.buckets.starts, getdate(day)) - 1
		return i if i >= 0 else None

	@property
	def labels(self) -> list[str]:
		return self.buckets.labels()

	def per_bucket(self, days) -> list[int]:
		counts = [0] * len(self.buckets.starts)
		for d in days:
			i = self.bucket(d)
			if i is not None:
				counts[i] += 1
		return counts

	def open_items(self) -> list:
		return [i for i in self.items if not i.is_closed]

	def overdue(self, item) -> bool:
		return not item.is_closed and item.due_date and getdate(item.due_date) < self.today

	def age(self, item) -> int:
		return (self.today - getdate(item.created)).days


# --------------------------------------------------------------------------- building blocks
def kpi(label, value, sub="", tone="blue", route=None):
	return {"label": label, "value": value, "sub": sub, "tone": tone, "route": route}


def counts(rows, key, label=None, limit=None):
	counter = Counter(label(r) if label else key(r) for r in rows)
	items = counter.most_common(limit)
	return [k for k, _n in items], [n for _k, n in items]


def aging(rows, today_, field):
	values = []
	for label, lo, hi in AGE_BUCKETS:
		values.append(sum(1 for r in rows if lo <= (today_ - getdate(field(r))).days <= hi))
	return [b[0] for b in AGE_BUCKETS], values


def avg(values):
	values = list(values)
	return round(sum(values) / len(values), 1) if values else None


def list_route(doctype, filters):
	return {"doctype": doctype, "filters": filters}


def empty(report_note):
	return {"kpis": [], "visuals": [], "note": report_note}


# --------------------------------------------------------------------------- reports
def report_delivery(c: Context) -> dict:
	if not c.items:
		return empty(_("No tickets yet."))
	open_, closed = c.open_items(), [i for i in c.items if i.is_closed]
	overdue = [i for i in open_ if c.overdue(i)]
	done_pct = round(len(closed) * 100 / len(c.items), 1)
	closed_in_range = [i for i in closed if i.closed_on and getdate(i.closed_on) >= c.start]
	cycle = avg((getdate(i.closed_on) - getdate(i.created)).days for i in closed_in_range)

	created = c.per_bucket(i.created for i in c.items)
	closed_trend = c.per_bucket(i.closed_on for i in closed)
	backlog = []
	for start in c.buckets.starts:
		end = start + timedelta(days=6 if c.buckets.kind == "week" else 27)
		backlog.append(
			sum(1 for i in c.items if getdate(i.created) <= end and (not i.is_closed or getdate(i.closed_on or end) > end))
		)
	statuses = counts(c.items, lambda i: i.status)
	priorities = counts(open_, lambda i: i.priority or _("Normal"))
	modules = defaultdict(lambda: [0, 0])
	for i in c.items:
		modules[c.module(i)][1 if i.is_closed else 0] += 1
	module_rows = sorted(modules.items(), key=lambda kv: -sum(kv[1]))[:10]
	age_labels, age_values = aging(open_, c.today, lambda i: i.created)
	top_overdue = sorted(overdue, key=lambda i: getdate(i.due_date))[:10]
	return {
		"kpis": [
			kpi(_("Tickets"), len(c.items), _("{0} open · {1} closed").format(len(open_), len(closed)), "blue", list_route("Work Item", {})),
			kpi(_("Completion"), f"{done_pct}%", "", "green"),
			kpi(_("Open"), len(open_), "", "purple", list_route("Work Item", {"is_closed": 0})),
			kpi(_("Overdue"), len(overdue), "", "red" if overdue else "teal", list_route("Work Item", {"is_closed": 0, "due_date": ["<", str(c.today)]})),
			kpi(_("Avg age of open"), f"{avg(c.age(i) for i in open_) or 0} d", "", "orange"),
			kpi(_("Avg days to close"), f"{cycle} d" if cycle is not None else "–", _("closed in range"), "cyan"),
		],
		"visuals": [
			{"title": _("Created vs closed"), "kind": "bar", "span": 2, "labels": c.labels, "datasets": [{"name": _("Created"), "values": created}, {"name": _("Closed"), "values": closed_trend}], "colors": ["blue", "green"]},
			{"title": _("Status mix"), "kind": "donut", "labels": statuses[0], "values": statuses[1]},
			{"title": _("Open backlog"), "kind": "line", "span": 2, "labels": c.labels, "datasets": [{"name": _("Open tickets"), "values": backlog}], "colors": ["purple"]},
			{"title": _("Open by priority"), "kind": "donut", "labels": priorities[0], "values": priorities[1]},
			{"title": _("Open vs closed by module"), "kind": "stack", "span": 2, "names": [_("Open"), _("Closed")], "tones": ["blue", "green"], "rows": [[k, v[0], v[1]] for k, v in module_rows]},
			{"title": _("Age of open tickets"), "kind": "bar", "labels": age_labels, "datasets": [{"name": _("Open"), "values": age_values}], "colors": ["orange"]},
			{"title": _("Most overdue"), "kind": "table", "span": 3, "columns": [_("Ticket"), _("Summary"), _("Owner"), _("Due"), _("Late")], "doctype": "Work Item",
			 "rows": [[i.name, i.subject, c.user(i.assigned_to), str(i.due_date), f"{(c.today - getdate(i.due_date)).days} d"] for i in top_overdue]},
		],
	}


def report_workload(c: Context) -> dict:
	if not c.items:
		return empty(_("No tickets yet."))
	open_ = c.open_items()
	people = defaultdict(lambda: {"open": 0, "overdue": 0, "est": 0.0, "spent": 0.0, "closed": 0})
	for i in c.items:
		p = people[c.user(i.assigned_to)]
		if i.is_closed:
			if i.closed_on and getdate(i.closed_on) >= c.start:
				p["closed"] += 1
		else:
			p["open"] += 1
			p["est"] += flt(i.estimated_hours)
			p["overdue"] += 1 if c.overdue(i) else 0
		p["spent"] += flt(i.spent_hours)
	rows = sorted(people.items(), key=lambda kv: -kv[1]["open"])
	named = [r for r in rows if r[0] != _("Unassigned")]
	top = rows[:12]
	return {
		"kpis": [
			kpi(_("People with work"), len(named), "", "blue"),
			kpi(_("Open tickets"), len(open_), "", "purple", list_route("Work Item", {"is_closed": 0})),
			kpi(_("Avg open per person"), round(len(open_) / max(len(named), 1), 1), "", "cyan"),
			kpi(_("Unassigned"), sum(1 for i in open_ if not i.assigned_to), "", "orange", list_route("Work Item", {"is_closed": 0, "assigned_to": ["is", "not set"]})),
			kpi(_("Overdue"), sum(1 for i in open_ if c.overdue(i)), "", "red"),
			kpi(_("Estimated hours open"), round(sum(flt(i.estimated_hours) for i in open_), 1), "", "teal"),
		],
		"visuals": [
			{"title": _("Open tickets per person"), "kind": "stack", "span": 2, "names": [_("On time"), _("Overdue")], "tones": ["blue", "red"], "rows": [[n, p["open"] - p["overdue"], p["overdue"]] for n, p in top]},
			{"title": _("Share of open work"), "kind": "donut", "labels": [n for n, _p in top[:8]], "values": [p["open"] for _n, p in top[:8]]},
			{"title": _("Closed in range"), "kind": "bar", "span": 2, "labels": [n for n, _p in top], "datasets": [{"name": _("Closed"), "values": [p["closed"] for _n, p in top]}], "colors": ["green"]},
			{"title": _("Hours: open estimate vs spent"), "kind": "bar", "labels": [n for n, _p in top[:8]], "datasets": [{"name": _("Estimated (open)"), "values": [round(p["est"], 1) for _n, p in top[:8]]}, {"name": _("Spent"), "values": [round(p["spent"], 1) for _n, p in top[:8]]}], "colors": ["purple", "orange"]},
			{"title": _("Workload table"), "kind": "table", "span": 3, "columns": [_("Person"), _("Open"), _("Overdue"), _("Est. hours"), _("Closed in range")],
			 "rows": [[n, p["open"], p["overdue"], round(p["est"], 1), p["closed"]] for n, p in rows]},
		],
	}


def report_releases(c: Context) -> dict:
	releases = frappe.get_all(
		"Release", filters={"project": ["in", c.projects or [""]]},
		fields=["name", "release_name", "project", "status", "due_date", "total_items", "closed_items", "percent_complete"], order_by="due_date",
	)
	sprints = frappe.get_all(
		"Sprint", filters={"project": ["in", c.projects or [""]]},
		fields=["name", "sprint_name", "project", "status", "start_date", "end_date", "total_items", "closed_items", "percent_complete"], order_by="start_date",
	)
	if not releases and not sprints:
		return empty(_("No releases or sprints yet."))
	open_rel = [r for r in releases if r.status != "Closed"]
	soon = [r for r in open_rel if r.due_date and 0 <= (getdate(r.due_date) - c.today).days <= 30]
	risk = [r for r in open_rel if r.due_date and (getdate(r.due_date) - c.today).days <= 14 and flt(r.percent_complete) < 100]
	by_month = Counter(getdate(r.due_date).strftime("%b %y") for r in releases if r.due_date)
	months = sorted(by_month, key=lambda m: date(2000 + int(m[-2:]), ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(m[:3]) + 1, 1))
	label = lambda r: r.release_name or r.name
	visuals = []
	if releases:
		visuals += [
			{"title": _("Release progress (%)"), "kind": "bar", "span": 2, "labels": [label(r) for r in releases], "datasets": [{"name": _("Complete %"), "values": [round(flt(r.percent_complete)) for r in releases]}], "colors": ["green"]},
			{"title": _("Releases due by month"), "kind": "bar", "labels": months, "datasets": [{"name": _("Releases"), "values": [by_month[m] for m in months]}], "colors": ["blue"]},
			{"title": _("Open vs closed tickets per release"), "kind": "stack", "span": 2, "names": [_("Open"), _("Closed")], "tones": ["blue", "green"], "rows": [[label(r), cint(r.total_items) - cint(r.closed_items), cint(r.closed_items)] for r in releases]},
			{"title": _("Release status"), "kind": "donut", "labels": list(Counter(r.status for r in releases)), "values": list(Counter(r.status for r in releases).values())},
		]
	done_sprints = [s for s in sprints if s.status == "Completed"] or sprints
	if sprints:
		visuals.append({"title": _("Sprint velocity (tickets closed)"), "kind": "bar", "span": 2, "labels": [s.sprint_name or s.name for s in done_sprints], "datasets": [{"name": _("Closed"), "values": [cint(s.closed_items) for s in done_sprints]}, {"name": _("Planned"), "values": [cint(s.total_items) for s in done_sprints]}], "colors": ["green", "purple"]})
	visuals.append({"title": _("Release schedule"), "kind": "table", "span": 3, "columns": [_("Release"), _("Project"), _("Due"), _("Days left"), _("Complete"), _("Status")], "doctype": "Release", "keys": [r.name for r in releases],
		"rows": [[label(r), c.names.get(r.project, r.project), str(r.due_date or ""), (getdate(r.due_date) - c.today).days if r.due_date else "", f"{round(flt(r.percent_complete))}%", r.status] for r in releases]})
	return {
		"kpis": [
			kpi(_("Releases"), len(releases), _("{0} open").format(len(open_rel)), "blue", list_route("Release", {})),
			kpi(_("Due in 30 days"), len(soon), "", "orange"),
			kpi(_("At risk"), len(risk), _("due within 14 days, not done"), "red" if risk else "teal"),
			kpi(_("Avg completion"), f"{avg(flt(r.percent_complete) for r in open_rel) or 0}%", _("open releases"), "green"),
			kpi(_("Sprints"), len(sprints), "", "purple", list_route("Sprint", {})),
			kpi(_("Avg sprint velocity"), avg(cint(s.closed_items) for s in done_sprints) or 0, _("tickets closed"), "cyan"),
		],
		"visuals": visuals,
	}


def report_quality(c: Context) -> dict:
	defects = frappe.get_all("Ticket Type", filters={"is_defect": 1}, pluck="name")
	if not defects:
		return empty(_('No defect ticket type. Open a Ticket Type (for example Bug) and tick "Counts as Defect".'))
	bugs = [i for i in c.items if i.tracker in defects]
	if not bugs:
		return empty(_("No bugs have been reported yet."))
	open_ = [i for i in bugs if not i.is_closed]
	closed_in_range = [i for i in bugs if i.is_closed and i.closed_on and getdate(i.closed_on) >= c.start]
	critical = [i for i in open_ if i.priority in ("Urgent", "Immediate")]
	opened = c.per_bucket(i.created for i in bugs)
	fixed = c.per_bucket(i.closed_on for i in bugs if i.is_closed)
	prio = counts(open_, lambda i: i.priority or _("Normal"))
	fix_days = defaultdict(list)
	for i in closed_in_range:
		fix_days[i.priority or _("Normal")].append((getdate(i.closed_on) - getdate(i.created)).days)
	modules = defaultdict(lambda: [0, 0])
	for i in bugs:
		modules[c.module(i)][1 if i.is_closed else 0] += 1
	age_labels, age_values = aging(open_, c.today, lambda i: i.created)
	oldest = sorted(open_, key=lambda i: getdate(i.created))[:10]
	in_range = [i for i in bugs if getdate(i.created) >= c.start]
	return {
		"kpis": [
			kpi(_("Open bugs"), len(open_), _("{0} fixed so far").format(len(bugs) - len(open_)), "orange", list_route("Work Item", {"tracker": ["in", defects], "is_closed": 0})),
			kpi(_("Critical open"), len(critical), "", "red" if critical else "teal"),
			kpi(_("Opened in range"), len(in_range), "", "purple"),
			kpi(_("Fixed in range"), len(closed_in_range), "", "green"),
			kpi(_("Avg days to fix"), avg(d for v in fix_days.values() for d in v) or "–", "", "cyan"),
			kpi(_("Bugs among tickets"), f"{round(len(bugs) * 100 / len(c.items))}%", "", "blue"),
		],
		"visuals": [
			{"title": _("Bugs opened vs fixed"), "kind": "bar", "span": 2, "labels": c.labels, "datasets": [{"name": _("Opened"), "values": opened}, {"name": _("Fixed"), "values": fixed}], "colors": ["orange", "green"]},
			{"title": _("Open bugs by priority"), "kind": "donut", "labels": prio[0], "values": prio[1]},
			{"title": _("Days to fix by priority"), "kind": "bar", "labels": list(fix_days), "datasets": [{"name": _("Days"), "values": [avg(v) for v in fix_days.values()]}], "colors": ["purple"]},
			{"title": _("Bugs by module"), "kind": "stack", "span": 2, "names": [_("Open"), _("Fixed")], "tones": ["orange", "green"], "rows": [[k, v[0], v[1]] for k, v in sorted(modules.items(), key=lambda kv: -sum(kv[1]))[:10]]},
			{"title": _("Age of open bugs"), "kind": "bar", "span": 3, "labels": age_labels, "datasets": [{"name": _("Open"), "values": age_values}], "colors": ["red"]},
			{"title": _("Oldest open bugs"), "kind": "table", "span": 3, "doctype": "Work Item", "columns": [_("Bug"), _("Summary"), _("Priority"), _("Owner"), _("Age")],
			 "rows": [[i.name, i.subject, i.priority or "", c.user(i.assigned_to), f"{c.age(i)} d"] for i in oldest]},
		],
	}


def report_client(c: Context) -> dict:
	waiting = [i for i in c.items if not i.is_closed and cint(i.dependent_on_client)]
	open_ = c.open_items()
	if not c.items:
		return empty(_("No tickets yet."))
	if not waiting:
		return {"kpis": [kpi(_("Waiting on client"), 0, _("Nothing is blocked on the client."), "green")], "visuals": []}
	since = lambda i: i.client_dependency_since or i.created
	days = [(c.today - getdate(since(i))).days for i in waiting]
	by_project = counts(waiting, lambda i: c.names.get(i.project, i.project))
	by_module = counts(waiting, lambda i: c.module(i), limit=10)
	age_labels, age_values = aging(waiting, c.today, since)
	oldest = sorted(waiting, key=lambda i: getdate(since(i)))[:15]
	return {
		"kpis": [
			kpi(_("Waiting on client"), len(waiting), "", "orange", list_route("Work Item", {"is_closed": 0, "dependent_on_client": 1})),
			kpi(_("Share of open work"), f"{round(len(waiting) * 100 / max(len(open_), 1))}%", "", "purple"),
			kpi(_("Avg wait"), f"{avg(days)} d", "", "cyan"),
			kpi(_("Longest wait"), f"{max(days)} d", "", "red" if max(days) > 14 else "teal"),
			kpi(_("Waiting over 14 days"), sum(1 for d in days if d > 14), "", "red"),
			kpi(_("Projects affected"), len(by_project[0]), "", "blue"),
		],
		"visuals": [
			{"title": _("How long they have waited"), "kind": "bar", "span": 2, "labels": age_labels, "datasets": [{"name": _("Tickets"), "values": age_values}], "colors": ["orange"]},
			{"title": _("Waiting by project"), "kind": "donut", "labels": by_project[0], "values": by_project[1]},
			{"title": _("Waiting by module"), "kind": "stack", "span": 3, "names": [_("Waiting")], "tones": ["orange"], "rows": [[k, v] for k, v in zip(*by_module)]},
			{"title": _("Longest waiting"), "kind": "table", "span": 3, "doctype": "Work Item", "columns": [_("Ticket"), _("Summary"), _("Owner"), _("Waiting since"), _("Days")],
			 "rows": [[i.name, i.subject, c.user(i.assigned_to), str(getdate(since(i))), (c.today - getdate(since(i))).days] for i in oldest]},
		],
	}


def report_time(c: Context) -> dict:
	entries = frappe.db.sql(
		"select user, project, date, hours, activity_type, is_billable from `tabTime Entry` where project in %(p)s and date >= %(start)s",
		{"p": c.projects or [""], "start": c.start}, as_dict=True,
	)
	if not entries:
		return empty(_("No time has been logged in this range."))
	total = sum(flt(e.hours) for e in entries)
	billable = sum(flt(e.hours) for e in entries if cint(e.is_billable))
	bill_b, non_b = [0.0] * len(c.buckets.starts), [0.0] * len(c.buckets.starts)
	for e in entries:
		i = c.bucket(e.date)
		if i is not None:
			(bill_b if cint(e.is_billable) else non_b)[i] += flt(e.hours)
	per_user, per_activity, per_project = defaultdict(lambda: [0.0, 0.0]), defaultdict(float), defaultdict(lambda: [0.0, 0.0])
	for e in entries:
		slot = 0 if cint(e.is_billable) else 1
		per_user[c.user(e.user)][slot] += flt(e.hours)
		per_project[c.names.get(e.project, e.project)][slot] += flt(e.hours)
		per_activity[e.activity_type or _("(none)")] += flt(e.hours)
	users = sorted(per_user.items(), key=lambda kv: -sum(kv[1]))
	weeks = max(len(c.buckets.starts), 1) if c.buckets.kind == "week" else max(len(c.buckets.starts), 1) * 4.33
	return {
		"kpis": [
			kpi(_("Hours logged"), round(total, 1), "", "blue", list_route("Time Entry", {})),
			kpi(_("Billable hours"), round(billable, 1), "", "green"),
			kpi(_("Billable share"), f"{round(billable * 100 / total) if total else 0}%", "", "purple"),
			kpi(_("Non-billable"), round(total - billable, 1), "", "orange"),
			kpi(_("People logging"), len(per_user), "", "cyan"),
			kpi(_("Avg hours / week"), round(total / weeks, 1), "", "teal"),
		],
		"visuals": [
			{"title": _("Hours over time"), "kind": "bar", "span": 2, "labels": c.labels, "datasets": [{"name": _("Billable"), "values": [round(v, 1) for v in bill_b]}, {"name": _("Non-billable"), "values": [round(v, 1) for v in non_b]}], "colors": ["green", "orange"]},
			{"title": _("By activity"), "kind": "donut", "labels": list(per_activity), "values": [round(v, 1) for v in per_activity.values()]},
			{"title": _("Hours per person"), "kind": "stack", "span": 2, "names": [_("Billable"), _("Non-billable")], "tones": ["green", "orange"], "rows": [[n, round(v[0], 1), round(v[1], 1)] for n, v in users[:12]]},
			{"title": _("Hours per project"), "kind": "stack", "names": [_("Billable"), _("Non-billable")], "tones": ["green", "orange"], "rows": [[n, round(v[0], 1), round(v[1], 1)] for n, v in sorted(per_project.items(), key=lambda kv: -sum(kv[1]))[:10]]},
		],
	}
