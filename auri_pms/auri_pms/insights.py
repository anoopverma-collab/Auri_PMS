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

from auri_pms.auri_pms.health import OPEN_NAME_CAP, make_buckets
from auri_pms.auri_pms.utils import insight_projects, nearest_indicator, portfolio_projects

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
	"tree": {
		"title": "Work Breakdown",
		"about": "Every ticket as a tree: project, module, release, sprint and status, with progress and hours at each level.",
		"icon": "tree",
	},
}

AGE_BUCKETS = [
	("0-7 d", 0, 7),
	("8-14 d", 8, 14),
	("15-30 d", 15, 30),
	("31-60 d", 31, 60),
	("60+ d", 61, 10**6),
]
ITEM_FIELDS = [
	"name",
	"subject",
	"project",
	"tracker",
	"status",
	"priority",
	"assigned_to",
	"project_module",
	"release",
	"sprint",
	"is_closed",
	"creation",
	"closed_on",
	"due_date",
	"estimated_hours",
	"spent_hours",
	"done_percent",
	"dependent_on_client",
	"client_dependency_since",
]


@frappe.whitelist()
def get_reports() -> list[dict]:
	"""The catalogue shown on the gallery page."""
	return [
		{"key": key, **{k: _(v) if k != "icon" else v for k, v in meta.items()}}
		for key, meta in REPORTS.items()
	]


@frappe.whitelist()
def get_insight(report: str, project: str | None = None, period: str = "3m") -> dict:
	"""One report for all projects the user sees, or for one project."""
	if report not in REPORTS:
		frappe.throw(_("Unknown report {0}").format(report))
	if not insight_projects() and portfolio_projects():  # a member whose roles do not include Insights
		frappe.throw(_("Auri Insights is not available to your Project Role"), frappe.PermissionError)
	projects = visible_projects(project)
	ctx = Context(projects, period)
	data = REPORT_FUNCTIONS[report](ctx)
	data.setdefault("title", _(REPORTS[report]["title"]))
	data["subtitle"] = _("{0} · {1}").format(
		project or _("1 project") if len(projects) == 1 else _("{0} projects").format(len(projects)),
		period_notes()[ctx.period],
	)
	data["period"] = ctx.period
	return data


def period_notes() -> dict[str, str]:
	# built per call: translations follow the user's language, which a module-level dict would fix at import time
	return {"1m": _("last month"), "3m": _("last 3 months"), "6m": _("last 6 months"), "all": _("overall")}


@frappe.whitelist()
def get_insight_projects() -> list[str]:
	"""The projects Insights covers for the user: Auri PMS projects where their Project Role has *Can See Auri Insights*
	(all of them for an admin).

	A public project the user is not a member of stays readable elsewhere but is not part of their analysis."""
	return insight_projects()


def visible_projects(project: str | None) -> list[str]:
	if project:
		if not frappe.db.exists("Project", project) or project not in get_insight_projects():
			frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
		return [project]
	return get_insight_projects()


class Context:
	"""The items, buckets and helpers every report shares."""

	def __init__(self, projects: list[str], period: str):
		self.projects = projects
		self.period = period if period in period_notes() else "3m"
		self.today = getdate(today())
		# get_list applies the Work Item permission query, so a member who sees only their own tickets gets the same limit here
		self.items = (
			frappe.get_list(
				"Work Item", filters={"project": ["in", projects]}, fields=ITEM_FIELDS, limit_page_length=0
			)
			if projects
			else []
		)
		for item in self.items:
			item.created = getdate(item.creation)
		earliest = min((i.created for i in self.items), default=None)
		self.buckets = make_buckets(self.period, earliest, self.today)
		self.start = self.buckets.first_day
		self.names = {
			p.name: p.project_name or p.name
			for p in frappe.get_all(
				"Project", filters={"name": ["in", projects or [""]]}, fields=["name", "project_name"]
			)
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
	for _label, lo, hi in AGE_BUCKETS:
		values.append(sum(1 for r in rows if lo <= (today_ - getdate(field(r))).days <= hi))
	return [b[0] for b in AGE_BUCKETS], values


def avg(values):
	values = list(values)
	return round(sum(values) / len(values), 1) if values else None


def list_route(doctype, filters):
	return {"doctype": doctype, "filters": filters}


EPOCH = "1900-01-01"


def span(start, end):
	"""A ``between`` filter for a date or datetime field."""
	return ["between", [str(start), str(end)]]


def wi(c, **filters):
	"""Work Item list route limited to the projects the report covers, so a count opens the same tickets."""
	return list_route("Work Item", {"project": ["in", c.projects or [""]], **filters})


def te(c, **filters):
	"""Time Entry list route for the report's projects and range."""
	return list_route(
		"Time Entry", {"project": ["in", c.projects or [""]], "date": [">=", str(c.start)], **filters}
	)


def user_filter(email):
	return email or ["is", "not set"]


def module_filter(names):
	"""Project Module filter for the module docnames behind one label ('' stands for no module)."""
	real = sorted(n for n in names if n)
	return ["in", real] if real else ["is", "not set"]


def bucket_routes(c, make):
	"""One route per time bucket; ``make(date_filter)`` builds it."""
	return [make(span(s, c.buckets.end(s))) for s in c.buckets.starts]


def age_routes(c, field, **base):
	"""One Work Item route per AGE_BUCKETS entry, filtering ``field`` to the dates that fall in that age."""
	out = []
	for _label, lo, hi in AGE_BUCKETS:
		first = EPOCH if hi >= 10**6 else c.today - timedelta(days=hi)
		out.append(wi(c, **base, **{field: span(first, c.today - timedelta(days=lo))}))
	return out


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
	backlog_routes = []
	for start in c.buckets.starts:
		end = start + timedelta(days=6 if c.buckets.kind == "week" else 27)
		open_then = [
			i
			for i in c.items
			if getdate(i.created) <= end and (not i.is_closed or getdate(i.closed_on or end) > end)
		]
		backlog.append(len(open_then))
		# the exact tickets behind the point; a very long list falls back to the ones still open now
		if len(open_then) <= OPEN_NAME_CAP:
			backlog_routes.append(wi(c, name=["in", [i.name for i in open_then] or ["-"]]))
		else:
			backlog_routes.append(wi(c, is_closed=0, creation=span(EPOCH, end)))
	statuses = counts(c.items, lambda i: i.status)
	priorities = counts(open_, lambda i: i.priority or "Normal")
	modules = defaultdict(lambda: [0, 0])
	module_names = defaultdict(set)  # label -> the real Project Module names behind it ('' = no module)
	for i in c.items:
		modules[c.module(i)][1 if i.is_closed else 0] += 1
		module_names[c.module(i)].add(i.project_module or "")
	module_rows = sorted(modules.items(), key=lambda kv: -sum(kv[1]))[:10]
	age_labels, age_values = aging(open_, c.today, lambda i: i.created)
	top_overdue = sorted(overdue, key=lambda i: getdate(i.due_date))[:10]
	return {
		"kpis": [
			kpi(
				_("Tickets"),
				len(c.items),
				_("{0} open · {1} closed").format(len(open_), len(closed)),
				"blue",
				wi(c),
			),
			kpi(_("Completion"), f"{done_pct}%", "", "green", wi(c, is_closed=1)),
			kpi(_("Open"), len(open_), "", "purple", wi(c, is_closed=0)),
			kpi(
				_("Overdue"),
				len(overdue),
				"",
				"red" if overdue else "teal",
				wi(c, is_closed=0, due_date=["<", str(c.today)]),
			),
			kpi(
				_("Avg age of open"),
				f"{avg(c.age(i) for i in open_) or 0} d",
				"",
				"orange",
				wi(c, is_closed=0),
			),
			kpi(
				_("Avg days to close"),
				f"{cycle} d" if cycle is not None else "-",
				_("closed in range"),
				"cyan",
				wi(c, is_closed=1, closed_on=span(c.start, c.today)),
			),
		],
		"visuals": [
			{
				"title": _("Created vs closed"),
				"kind": "bar",
				"span": 2,
				"labels": c.labels,
				"datasets": [
					{"name": _("Created"), "values": created},
					{"name": _("Closed"), "values": closed_trend},
				],
				"routes": [
					bucket_routes(c, lambda r: wi(c, creation=r)),
					bucket_routes(c, lambda r: wi(c, is_closed=1, closed_on=r)),
				],
				"colors": ["blue", "green"],
			},
			{
				"title": _("Status mix"),
				"kind": "donut",
				"labels": statuses[0],
				"values": statuses[1],
				"routes": [wi(c, status=k) for k in statuses[0]],
			},
			{
				"title": _("Open backlog"),
				"kind": "line",
				"span": 2,
				"labels": c.labels,
				"datasets": [{"name": _("Open tickets"), "values": backlog}],
				"routes": [backlog_routes],
				"colors": ["purple"],
			},
			{
				"title": _("Open by priority"),
				"kind": "donut",
				"labels": priorities[0],
				"values": priorities[1],
				"routes": [wi(c, is_closed=0, priority=k) for k in priorities[0]],
			},
			{
				"title": _("Open vs closed by module"),
				"kind": "stack",
				"span": 2,
				"names": [_("Open"), _("Closed")],
				"tones": ["blue", "green"],
				"rows": [[k, v[0], v[1]] for k, v in module_rows],
				"routes": [
					[
						wi(c, project_module=module_filter(module_names[k]), is_closed=0),
						wi(c, project_module=module_filter(module_names[k]), is_closed=1),
					]
					for k, _v in module_rows
				],
				"row_routes": [wi(c, project_module=module_filter(module_names[k])) for k, _v in module_rows],
			},
			{
				"title": _("Age of open tickets"),
				"kind": "bar",
				"labels": age_labels,
				"datasets": [{"name": _("Open"), "values": age_values}],
				"routes": [age_routes(c, "creation", is_closed=0)],
				"colors": ["orange"],
			},
			{
				"title": _("Most overdue"),
				"kind": "table",
				"span": 3,
				"columns": [_("Ticket"), _("Summary"), _("Owner"), _("Due"), _("Late")],
				"doctype": "Work Item",
				"rows": [
					[
						i.name,
						i.subject,
						c.user(i.assigned_to),
						str(i.due_date),
						f"{(c.today - getdate(i.due_date)).days} d",
					]
					for i in top_overdue
				],
			},
		],
	}


def report_workload(c: Context) -> dict:
	if not c.items:
		return empty(_("No tickets yet."))
	open_ = c.open_items()
	# keyed by the user's email (None = unassigned) so a row can open that person's tickets; c.user() gives the label
	people = defaultdict(lambda: {"open": 0, "overdue": 0, "est": 0.0, "spent": 0.0, "closed": 0})
	for i in c.items:
		p = people[i.assigned_to or None]
		if i.is_closed:
			if i.closed_on and getdate(i.closed_on) >= c.start:
				p["closed"] += 1
		else:
			p["open"] += 1
			p["est"] += flt(i.estimated_hours)
			p["overdue"] += 1 if c.overdue(i) else 0
		p["spent"] += flt(i.spent_hours)
	rows = sorted(people.items(), key=lambda kv: -kv[1]["open"])
	named = [r for r in rows if r[0]]
	late_filter = {"is_closed": 0, "due_date": ["<", str(c.today)]}
	closed_filter = {"is_closed": 1, "closed_on": [">=", str(c.start)]}

	def of(email, **f):
		return wi(c, assigned_to=user_filter(email), **f)

	top = rows[:12]
	return {
		"kpis": [
			kpi(_("People with work"), len(named), "", "blue", wi(c, assigned_to=["is", "set"])),
			kpi(_("Open tickets"), len(open_), "", "purple", wi(c, is_closed=0)),
			kpi(
				_("Avg open per person"),
				round(len(open_) / max(len(named), 1), 1),
				"",
				"cyan",
				wi(c, is_closed=0),
			),
			kpi(
				_("Unassigned"),
				sum(1 for i in open_ if not i.assigned_to),
				"",
				"orange",
				wi(c, is_closed=0, assigned_to=["is", "not set"]),
			),
			kpi(_("Overdue"), sum(1 for i in open_ if c.overdue(i)), "", "red", wi(c, **late_filter)),
			kpi(
				_("Estimated hours open"),
				round(sum(flt(i.estimated_hours) for i in open_), 1),
				"",
				"teal",
				wi(c, is_closed=0),
			),
		],
		"visuals": [
			{
				"title": _("Open tickets per person"),
				"kind": "stack",
				"span": 2,
				"names": [_("On time"), _("Overdue")],
				"tones": ["blue", "red"],
				"rows": [[c.user(e), p["open"] - p["overdue"], p["overdue"]] for e, p in top],
				# approximate: "On time" cannot be told apart from overdue in the list (tickets with no due date), so
				# that segment opens all of the person's open tickets
				"routes": [[of(e, is_closed=0), of(e, **late_filter)] for e, _p in top],
				"row_routes": [of(e, is_closed=0) for e, _p in top],
			},
			{
				"title": _("Share of open work"),
				"kind": "donut",
				"labels": [c.user(e) for e, _p in top[:8]],
				"values": [p["open"] for _e, p in top[:8]],
				"routes": [of(e, is_closed=0) for e, _p in top[:8]],
			},
			{
				"title": _("Closed in range"),
				"kind": "bar",
				"span": 2,
				"labels": [c.user(e) for e, _p in top],
				"datasets": [{"name": _("Closed"), "values": [p["closed"] for _e, p in top]}],
				"routes": [[of(e, **closed_filter) for e, _p in top]],
				"colors": ["green"],
			},
			{
				"title": _("Hours: open estimate vs spent"),
				"kind": "bar",
				"labels": [c.user(e) for e, _p in top[:8]],
				"datasets": [
					{"name": _("Estimated (open)"), "values": [round(p["est"], 1) for _e, p in top[:8]]},
					{"name": _("Spent"), "values": [round(p["spent"], 1) for _e, p in top[:8]]},
				],
				"routes": [
					[of(e, is_closed=0) for e, _p in top[:8]],
					[of(e) for e, _p in top[:8]],  # spent hours are summed over all of the person's tickets
				],
				"colors": ["purple", "orange"],
			},
			{
				"title": _("Workload table"),
				"kind": "table",
				"span": 3,
				"columns": [_("Person"), _("Open"), _("Overdue"), _("Est. hours"), _("Closed in range")],
				"rows": [
					[c.user(e), p["open"], p["overdue"], round(p["est"], 1), p["closed"]] for e, p in rows
				],
				"cell_routes": [
					[
						of(e),
						of(e, is_closed=0),
						of(e, **late_filter),
						of(e, is_closed=0),
						of(e, **closed_filter),
					]
					for e, _p in rows
				],
			},
		],
	}


def report_releases(c: Context) -> dict:
	releases = frappe.get_all(
		"Release",
		filters={"project": ["in", c.projects or [""]]},
		fields=[
			"name",
			"release_name",
			"project",
			"status",
			"due_date",
			"total_items",
			"closed_items",
			"percent_complete",
		],
		order_by="due_date",
	)
	sprints = frappe.get_all(
		"Sprint",
		filters={"project": ["in", c.projects or [""]]},
		fields=[
			"name",
			"sprint_name",
			"project",
			"status",
			"start_date",
			"end_date",
			"total_items",
			"closed_items",
			"percent_complete",
		],
		order_by="start_date",
	)
	if not releases and not sprints:
		return empty(_("No releases or sprints yet."))
	open_rel = [r for r in releases if r.status != "Closed"]
	soon = [r for r in open_rel if r.due_date and 0 <= (getdate(r.due_date) - c.today).days <= 30]
	risk = [
		r
		for r in open_rel
		if r.due_date and (getdate(r.due_date) - c.today).days <= 14 and flt(r.percent_complete) < 100
	]
	by_month = Counter(getdate(r.due_date).strftime("%b %y") for r in releases if r.due_date)

	def month_start(m):
		return date(
			2000 + int(m[-2:]),
			["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(m[:3])
			+ 1,
			1,
		)

	months = sorted(by_month, key=month_start)

	def month_range(m):
		first = month_start(m)
		return span(first, (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1))

	rel_scope = {"project": ["in", c.projects or [""]]}

	def label(r):
		return r.release_name or r.name

	visuals = []
	if releases:
		visuals += [
			{
				"title": _("Release progress (%)"),
				"kind": "bar",
				"span": 2,
				"labels": [label(r) for r in releases],
				"datasets": [
					{"name": _("Complete %"), "values": [round(flt(r.percent_complete)) for r in releases]}
				],
				"routes": [[wi(c, release=r.name) for r in releases]],
				"colors": ["green"],
			},
			{
				"title": _("Releases due by month"),
				"kind": "bar",
				"labels": months,
				"datasets": [{"name": _("Releases"), "values": [by_month[m] for m in months]}],
				"routes": [
					[list_route("Release", {**rel_scope, "due_date": month_range(m)}) for m in months]
				],
				"colors": ["blue"],
			},
			{
				"title": _("Open vs closed tickets per release"),
				"kind": "stack",
				"span": 2,
				"names": [_("Open"), _("Closed")],
				"tones": ["blue", "green"],
				"rows": [
					[label(r), cint(r.total_items) - cint(r.closed_items), cint(r.closed_items)]
					for r in releases
				],
				"routes": [
					[wi(c, release=r.name, is_closed=0), wi(c, release=r.name, is_closed=1)] for r in releases
				],
				"row_routes": [wi(c, release=r.name) for r in releases],
			},
			{
				"title": _("Release status"),
				"kind": "donut",
				"labels": list(Counter(r.status for r in releases)),
				"values": list(Counter(r.status for r in releases).values()),
				"routes": [
					list_route("Release", {**rel_scope, "status": k})
					for k in Counter(r.status for r in releases)
				],
			},
		]
	done_sprints = [s for s in sprints if s.status == "Completed"] or sprints
	if sprints:
		visuals.append(
			{
				"title": _("Sprint velocity (tickets closed)"),
				"kind": "bar",
				"span": 2,
				"labels": [s.sprint_name or s.name for s in done_sprints],
				"datasets": [
					{"name": _("Closed"), "values": [cint(s.closed_items) for s in done_sprints]},
					{"name": _("Planned"), "values": [cint(s.total_items) for s in done_sprints]},
				],
				"routes": [
					[wi(c, sprint=s.name, is_closed=1) for s in done_sprints],
					[wi(c, sprint=s.name) for s in done_sprints],
				],
				"colors": ["green", "purple"],
			}
		)
	visuals.append(
		{
			"title": _("Release schedule"),
			"kind": "table",
			"span": 3,
			"columns": [_("Release"), _("Project"), _("Due"), _("Days left"), _("Complete"), _("Status")],
			"doctype": "Release",
			"keys": [r.name for r in releases],
			"row_routes": [list_route("Release", {"name": r.name}) for r in releases],
			"rows": [
				[
					label(r),
					c.names.get(r.project, r.project),
					str(r.due_date or ""),
					(getdate(r.due_date) - c.today).days if r.due_date else "",
					f"{round(flt(r.percent_complete))}%",
					r.status,
				]
				for r in releases
			],
		}
	)
	return {
		"kpis": [
			kpi(
				_("Releases"),
				len(releases),
				_("{0} open").format(len(open_rel)),
				"blue",
				list_route("Release", rel_scope),
			),
			kpi(
				_("Due in 30 days"),
				len(soon),
				"",
				"orange",
				list_route(
					"Release",
					{
						**rel_scope,
						"status": ["!=", "Closed"],
						"due_date": span(c.today, c.today + timedelta(days=30)),
					},
				),
			),
			kpi(
				_("At risk"),
				len(risk),
				_("due within 14 days, not done"),
				"red" if risk else "teal",
				list_route(
					"Release",
					{
						**rel_scope,
						"status": ["!=", "Closed"],
						"due_date": ["<=", str(c.today + timedelta(days=14))],
						"percent_complete": ["<", 100],
					},
				),
			),
			kpi(
				_("Avg completion"),
				f"{avg(flt(r.percent_complete) for r in open_rel) or 0}%",
				_("open releases"),
				"green",
				list_route("Release", {**rel_scope, "status": ["!=", "Closed"]}),
			),
			kpi(_("Sprints"), len(sprints), "", "purple", list_route("Sprint", rel_scope)),
			kpi(
				_("Avg sprint velocity"),
				avg(cint(s.closed_items) for s in done_sprints) or 0,
				_("tickets closed"),
				"cyan",
				# the sprints it averages over: completed ones, or all when none is completed yet
				list_route(
					"Sprint",
					{
						**rel_scope,
						**({"status": "Completed"} if any(s.status == "Completed" for s in sprints) else {}),
					},
				),
			),
		],
		"visuals": visuals,
	}


def report_quality(c: Context) -> dict:
	defects = frappe.get_all("Ticket Type", filters={"is_defect": 1}, pluck="name")
	if not defects:
		return empty(
			_('No defect ticket type. Open a Ticket Type (for example Bug) and tick "Counts as Defect".')
		)
	bugs = [i for i in c.items if i.tracker in defects]
	if not bugs:
		return empty(_("No bugs have been reported yet."))
	open_ = [i for i in bugs if not i.is_closed]
	closed_in_range = [i for i in bugs if i.is_closed and i.closed_on and getdate(i.closed_on) >= c.start]
	critical = [i for i in open_ if i.priority in ("Urgent", "Immediate")]
	opened = c.per_bucket(i.created for i in bugs)
	fixed = c.per_bucket(i.closed_on for i in bugs if i.is_closed)
	prio = counts(open_, lambda i: i.priority or "Normal")
	fix_days = defaultdict(list)
	for i in closed_in_range:
		fix_days[i.priority or "Normal"].append((getdate(i.closed_on) - getdate(i.created)).days)
	modules = defaultdict(lambda: [0, 0])
	module_names = defaultdict(set)  # label -> the real Project Module names behind it ('' = no module)
	for i in bugs:
		modules[c.module(i)][1 if i.is_closed else 0] += 1
		module_names[c.module(i)].add(i.project_module or "")
	top_modules = sorted(modules.items(), key=lambda kv: -sum(kv[1]))[:10]
	bug = {"tracker": ["in", defects]}
	age_labels, age_values = aging(open_, c.today, lambda i: i.created)
	oldest = sorted(open_, key=lambda i: getdate(i.created))[:10]
	in_range = [i for i in bugs if getdate(i.created) >= c.start]
	return {
		"kpis": [
			kpi(
				_("Open bugs"),
				len(open_),
				_("{0} fixed so far").format(len(bugs) - len(open_)),
				"orange",
				wi(c, **bug, is_closed=0),
			),
			kpi(
				_("Critical open"),
				len(critical),
				"",
				"red" if critical else "teal",
				wi(c, **bug, is_closed=0, priority=["in", ["Urgent", "Immediate"]]),
			),
			kpi(
				_("Opened in range"),
				len(in_range),
				"",
				"purple",
				wi(c, **bug, creation=span(c.start, c.today)),
			),
			kpi(
				_("Fixed in range"),
				len(closed_in_range),
				"",
				"green",
				wi(c, **bug, is_closed=1, closed_on=span(c.start, c.today)),
			),
			kpi(
				_("Avg days to fix"),
				avg(d for v in fix_days.values() for d in v) or "-",
				"",
				"cyan",
				wi(c, **bug, is_closed=1, closed_on=span(c.start, c.today)),
			),
			kpi(
				_("Bugs among tickets"), f"{round(len(bugs) * 100 / len(c.items))}%", "", "blue", wi(c, **bug)
			),
		],
		"visuals": [
			{
				"title": _("Bugs opened vs fixed"),
				"kind": "bar",
				"span": 2,
				"labels": c.labels,
				"datasets": [{"name": _("Opened"), "values": opened}, {"name": _("Fixed"), "values": fixed}],
				"routes": [
					bucket_routes(c, lambda r: wi(c, **bug, creation=r)),
					bucket_routes(c, lambda r: wi(c, **bug, is_closed=1, closed_on=r)),
				],
				"colors": ["orange", "green"],
			},
			{
				"title": _("Open bugs by priority"),
				"kind": "donut",
				"labels": prio[0],
				"values": prio[1],
				"routes": [wi(c, **bug, is_closed=0, priority=k) for k in prio[0]],
			},
			{
				"title": _("Days to fix by priority"),
				"kind": "bar",
				"labels": list(fix_days),
				"datasets": [{"name": _("Days"), "values": [avg(v) for v in fix_days.values()]}],
				"routes": [
					[
						wi(c, **bug, is_closed=1, closed_on=span(c.start, c.today), priority=k)
						for k in fix_days
					]
				],
				"colors": ["purple"],
			},
			{
				"title": _("Bugs by module"),
				"kind": "stack",
				"span": 2,
				"names": [_("Open"), _("Fixed")],
				"tones": ["orange", "green"],
				"rows": [[k, v[0], v[1]] for k, v in top_modules],
				"routes": [
					[
						wi(c, **bug, project_module=module_filter(module_names[k]), is_closed=0),
						wi(c, **bug, project_module=module_filter(module_names[k]), is_closed=1),
					]
					for k, _v in top_modules
				],
				"row_routes": [
					wi(c, **bug, project_module=module_filter(module_names[k])) for k, _v in top_modules
				],
			},
			{
				"title": _("Age of open bugs"),
				"kind": "bar",
				"span": 3,
				"labels": age_labels,
				"datasets": [{"name": _("Open"), "values": age_values}],
				"routes": [age_routes(c, "creation", **bug, is_closed=0)],
				"colors": ["red"],
			},
			{
				"title": _("Oldest open bugs"),
				"kind": "table",
				"span": 3,
				"doctype": "Work Item",
				"columns": [_("Bug"), _("Summary"), _("Priority"), _("Owner"), _("Age")],
				"rows": [
					[i.name, i.subject, i.priority or "", c.user(i.assigned_to), f"{c.age(i)} d"]
					for i in oldest
				],
			},
		],
	}


def report_client(c: Context) -> dict:
	waiting = [i for i in c.items if not i.is_closed and cint(i.dependent_on_client)]
	open_ = c.open_items()
	if not c.items:
		return empty(_("No tickets yet."))
	if not waiting:
		return {
			"kpis": [
				kpi(
					_("Waiting on client"),
					0,
					_("Nothing is blocked on the client."),
					"green",
					wi(c, is_closed=0, dependent_on_client=1),
				)
			],
			"visuals": [],
		}

	def since(i):
		return i.client_dependency_since or i.created

	days = [(c.today - getdate(since(i))).days for i in waiting]
	by_project = counts(waiting, lambda i: i.project)  # project names; labels come from c.names
	by_module = counts(waiting, lambda i: c.module(i), limit=10)
	module_names = defaultdict(set)  # label -> the real Project Module names behind it ('' = no module)
	for i in waiting:
		module_names[c.module(i)].add(i.project_module or "")
	wait = {"is_closed": 0, "dependent_on_client": 1}
	age_labels, age_values = aging(waiting, c.today, since)
	oldest = sorted(waiting, key=lambda i: getdate(since(i)))[:15]
	return {
		"kpis": [
			kpi(
				_("Waiting on client"),
				len(waiting),
				"",
				"orange",
				wi(c, **wait),
			),
			kpi(
				_("Share of open work"),
				f"{round(len(waiting) * 100 / max(len(open_), 1))}%",
				"",
				"purple",
				wi(c, **wait),
			),
			kpi(_("Avg wait"), f"{avg(days)} d", "", "cyan", wi(c, **wait)),
			kpi(_("Longest wait"), f"{max(days)} d", "", "red" if max(days) > 14 else "teal", wi(c, **wait)),
			kpi(
				_("Waiting over 14 days"),
				sum(1 for d in days if d > 14),
				"",
				"red",
				# approximate: waiting-since falls back to the creation date for tickets that have no
				# "client dependency since" date, which a list filter cannot express
				wi(c, **wait, client_dependency_since=["<", str(c.today - timedelta(days=14))]),
			),
			kpi(_("Projects affected"), len(by_project[0]), "", "blue", wi(c, **wait)),
		],
		"visuals": [
			{
				"title": _("How long they have waited"),
				"kind": "bar",
				"span": 2,
				"labels": age_labels,
				"datasets": [{"name": _("Tickets"), "values": age_values}],
				# approximate: a ticket with no "client dependency since" date is aged from its creation date in the
				# chart but cannot be matched by that rule in a list filter, so it is left out of the opened list
				"routes": [age_routes(c, "client_dependency_since", **wait)],
				"colors": ["orange"],
			},
			{
				"title": _("Waiting by project"),
				"kind": "donut",
				"labels": [c.names.get(k, k) for k in by_project[0]],
				"values": by_project[1],
				"routes": [wi(c, **wait, project=k) for k in by_project[0]],
			},
			{
				"title": _("Waiting by module"),
				"kind": "stack",
				"span": 3,
				"names": [_("Waiting")],
				"tones": ["orange"],
				"rows": [[k, v] for k, v in zip(*by_module, strict=True)],
				"routes": [
					[wi(c, **wait, project_module=module_filter(module_names[k]))] for k in by_module[0]
				],
				"row_routes": [
					wi(c, **wait, project_module=module_filter(module_names[k])) for k in by_module[0]
				],
			},
			{
				"title": _("Longest waiting"),
				"kind": "table",
				"span": 3,
				"doctype": "Work Item",
				"columns": [_("Ticket"), _("Summary"), _("Owner"), _("Waiting since"), _("Days")],
				"rows": [
					[
						i.name,
						i.subject,
						c.user(i.assigned_to),
						str(getdate(since(i))),
						(c.today - getdate(since(i))).days,
					]
					for i in oldest
				],
			},
		],
	}


def report_tree(c: Context) -> dict:
	"""Project > Module > Release > Sprint > status, with counts, progress and hours on every level.

	A ticket is in range when it is still open, or was created or closed inside the period, so the
	backlog never drops out of the picture while old closed work does.
	"""
	items = [
		i
		for i in c.items
		if not i.is_closed or i.created >= c.start or (i.closed_on and getdate(i.closed_on) >= c.start)
	]
	if not items:
		return empty(_("No tickets in this period."))
	releases = {
		r.name: r
		for r in frappe.get_all(
			"Release",
			filters={"project": ["in", c.projects or [""]]},
			fields=["name", "release_name", "due_date"],
		)
	}
	sprints = {
		s.name: s
		for s in frappe.get_all(
			"Sprint",
			filters={"project": ["in", c.projects or [""]]},
			fields=["name", "sprint_name", "start_date", "end_date"],
		)
	}
	statuses = frappe.get_all(
		"Work Item Status", fields=["name", "color", "sequence"], order_by="sequence asc, name asc"
	)
	order = {s.name: n for n, s in enumerate(statuses)}
	tone = {s.name: nearest_indicator(s.color) for s in statuses}

	def label_dates(a, b):
		fmt = frappe.utils.formatdate
		return f"{fmt(a)} - {fmt(b)}" if a and b else ""

	def numbers(rows):
		est = sum(flt(i.estimated_hours) for i in rows)
		spent = sum(flt(i.spent_hours) for i in rows)
		closed = sum(1 for i in rows if i.is_closed)
		return {
			"tickets": len(rows),
			"closed": closed,
			"overdue": sum(1 for i in rows if c.overdue(i)),
			"est": round(est, 1),
			"spent": round(spent, 1),
			"pct": round(closed * 100 / len(rows)) if rows else 0,
		}

	def group(rows, key):
		out = defaultdict(list)
		for i in rows:
			out[key(i)].append(i)
		return out

	def filters_of(i, **extra):
		f = {"project": i.project}
		f.update({k: v for k, v in extra.items() if v})
		return f

	def build_status(rows, base):
		out = []
		for st, group_rows in sorted(
			group(rows, lambda i: i.status).items(), key=lambda kv: order.get(kv[0], 99)
		):
			out.append(
				{
					"kind": "Status",
					"label": _(st),
					"tone": tone.get(st, "gray"),
					**numbers(group_rows),
					"route": list_route("Work Item", {**base, "status": st}),
					"children": [],
				}
			)
		return out

	def build_sprints(rows, base):
		out = []
		for key, group_rows in group(rows, lambda i: i.sprint or "").items():
			sp = sprints.get(key)
			b = {**base, "sprint": key} if key else base
			out.append(
				{
					"kind": "Sprint",
					"label": sp.sprint_name if sp else _("Backlog (no sprint)"),
					"meta": label_dates(sp.start_date, sp.end_date) if sp else "",
					"none": not key,
					"sort": str(sp.start_date or "") if sp else "",
					**numbers(group_rows),
					"route": list_route("Work Item", b),
					"children": build_status(group_rows, b),
				}
			)
		return sorted(out, key=lambda n: (n["none"], n["sort"] == "", n["sort"], n["label"]))

	def build_releases(rows, base):
		out = []
		for key, group_rows in group(rows, lambda i: i.release or "").items():
			rl = releases.get(key)
			b = {**base, "release": key} if key else base
			out.append(
				{
					"kind": "Release",
					"label": rl.release_name if rl else _("No release"),
					"meta": _("due {0}").format(frappe.utils.formatdate(rl.due_date))
					if rl and rl.due_date
					else "",
					"none": not key,
					"sort": str(rl.due_date or "") if rl else "",
					**numbers(group_rows),
					"route": list_route("Work Item", b),
					"children": build_sprints(group_rows, b),
				}
			)
		return sorted(out, key=lambda n: (n["none"], n["sort"] == "", n["sort"], n["label"]))

	def build_modules(rows, base):
		out = []
		for key, group_rows in group(rows, lambda i: i.project_module or "").items():
			b = {**base, "project_module": key} if key else base
			out.append(
				{
					"kind": "Module",
					"label": c.module(group_rows[0]) if key else _("(no module)"),
					"none": not key,
					**numbers(group_rows),
					"route": list_route("Work Item", b),
					"children": build_releases(group_rows, b),
				}
			)
		return sorted(out, key=lambda n: (n["none"], n["label"]))

	tree = []
	for project, rows in sorted(
		group(items, lambda i: i.project).items(), key=lambda kv: c.names.get(kv[0], kv[0])
	):
		base = {"project": project}
		tree.append(
			{
				"kind": "Project",
				"label": c.names.get(project, project),
				**numbers(rows),
				"route": list_route("Work Item", base),
				"children": build_modules(rows, base),
			}
		)
	total = numbers(items)
	owed = round(
		sum(max(flt(i.estimated_hours) - flt(i.spent_hours), 0) for i in items if not i.is_closed), 1
	)
	late_projects = len({i.project for i in items if c.overdue(i)})
	return {
		"kpis": [
			# approximate: "in range" is open tickets plus those closed in the period, which one list filter cannot
			# express, so the count opens every ticket of the projects (the open ones, and all the closed ones)
			kpi(
				_("Tickets"),
				total["tickets"],
				_("{0} open · {1} closed").format(total["tickets"] - total["closed"], total["closed"]),
				"blue",
				wi(c),
			),
			kpi(
				_("Closed"),
				f"{total['pct']}%",
				_("of all tickets in range"),
				"green",
				wi(c, is_closed=1, closed_on=span(c.start, c.today)),
			),
			kpi(
				_("Overdue"),
				total["overdue"],
				_("across {0} projects").format(late_projects),
				"red" if total["overdue"] else "teal",
				list_route("Work Item", {"is_closed": 0, "due_date": ["<", str(c.today)]}),
			),
			kpi(
				_("Hours still owed"),
				f"{owed:g} h",
				_("{0} h estimated · {1} h spent").format(f"{total['est']:g}", f"{total['spent']:g}"),
				"orange",
				wi(c, is_closed=0),
			),
		],
		"visuals": [
			{
				"kind": "tree",
				"title": _("Project > Module > Release > Sprint > Status"),
				"span": 3,
				"tree": tree,
			}
		],
	}


def report_time(c: Context) -> dict:
	entries = frappe.db.sql(
		"select user, project, date, hours, activity_type, is_billable from `tabTime Entry` where project in %(p)s and date >= %(start)s",
		{"p": c.projects or [""], "start": c.start},
		as_dict=True,
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
	in_range = te(c)
	per_user, per_activity, per_project = (
		defaultdict(lambda: [0.0, 0.0]),
		defaultdict(float),
		defaultdict(lambda: [0.0, 0.0]),
	)
	for e in entries:
		slot = 0 if cint(e.is_billable) else 1
		per_user[e.user][slot] += flt(e.hours)
		per_project[e.project][slot] += flt(e.hours)
		per_activity[e.activity_type or ""] += flt(e.hours)
	users = sorted(per_user.items(), key=lambda kv: -sum(kv[1]))
	top_projects = sorted(per_project.items(), key=lambda kv: -sum(kv[1]))[:10]
	weeks = (
		max(len(c.buckets.starts), 1) if c.buckets.kind == "week" else max(len(c.buckets.starts), 1) * 4.33
	)
	return {
		"kpis": [
			kpi(_("Hours logged"), round(total, 1), "", "blue", in_range),
			kpi(_("Billable hours"), round(billable, 1), "", "green", te(c, is_billable=1)),
			kpi(
				_("Billable share"),
				f"{round(billable * 100 / total) if total else 0}%",
				"",
				"purple",
				in_range,
			),
			kpi(_("Non-billable"), round(total - billable, 1), "", "orange", te(c, is_billable=0)),
			kpi(_("People logging"), len(per_user), "", "cyan", in_range),
			kpi(_("Avg hours / week"), round(total / weeks, 1), "", "teal", in_range),
		],
		"visuals": [
			{
				"title": _("Hours over time"),
				"kind": "bar",
				"span": 2,
				"labels": c.labels,
				"datasets": [
					{"name": _("Billable"), "values": [round(v, 1) for v in bill_b]},
					{"name": _("Non-billable"), "values": [round(v, 1) for v in non_b]},
				],
				"routes": [
					bucket_routes(c, lambda r: te(c, is_billable=1, date=r)),
					bucket_routes(c, lambda r: te(c, is_billable=0, date=r)),
				],
				"colors": ["green", "orange"],
			},
			{
				"title": _("By activity"),
				"kind": "donut",
				"labels": [a or _("(none)") for a in per_activity],
				"values": [round(v, 1) for v in per_activity.values()],
				"routes": [te(c, activity_type=a or ["is", "not set"]) for a in per_activity],
			},
			{
				"title": _("Hours per person"),
				"kind": "stack",
				"span": 2,
				"names": [_("Billable"), _("Non-billable")],
				"tones": ["green", "orange"],
				"rows": [[c.user(u), round(v[0], 1), round(v[1], 1)] for u, v in users[:12]],
				"routes": [
					[te(c, user=u, is_billable=1), te(c, user=u, is_billable=0)] for u, _v in users[:12]
				],
				"row_routes": [te(c, user=u) for u, _v in users[:12]],
			},
			{
				"title": _("Hours per project"),
				"kind": "stack",
				"names": [_("Billable"), _("Non-billable")],
				"tones": ["green", "orange"],
				"rows": [[c.names.get(n, n), round(v[0], 1), round(v[1], 1)] for n, v in top_projects],
				"routes": [
					[te(c, project=n, is_billable=1), te(c, project=n, is_billable=0)]
					for n, _v in top_projects
				],
				"row_routes": [te(c, project=n) for n, _v in top_projects],
			},
		],
	}


REPORT_FUNCTIONS = {
	"delivery": report_delivery,
	"workload": report_workload,
	"releases": report_releases,
	"quality": report_quality,
	"client": report_client,
	"tree": report_tree,
	"time": report_time,
}
