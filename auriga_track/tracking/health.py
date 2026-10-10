"""Project health: ticket flow, workload, billable time and an overall status for one project."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from auriga_track.tracking.utils import get_burndown

AGE_BUCKETS = (
	(7, "0-7d"),
	(14, "8-14d"),
	(30, "15-30d"),
	(60, "31-60d"),
	(10**6, "60d+"),
)


def monday(day: date) -> date:
	"""Return the Monday of the week containing ``day``."""
	return day - timedelta(days=day.weekday())


PERIOD_WEEKS = {"1m": 5, "3m": 13, "6m": 26}
PERIODS = ("1m", "3m", "6m", "all")
MAX_WEEKLY_BUCKETS = 26
MAX_MONTHLY_BUCKETS = 36


class Buckets:
	"""Time buckets of a dashboard period: weeks (Monday start) or, for long ranges, calendar months."""

	def __init__(self, kind: str, starts: list[date], today_: date) -> None:
		self.kind, self.starts, self.today = kind, starts, today_

	def key(self, day: date) -> date:
		"""Start of the bucket ``day`` falls in."""
		return monday(day) if self.kind == "week" else day.replace(day=1)

	def end(self, start: date) -> date:
		"""Last day of the bucket, capped at today."""
		if self.kind == "week":
			stop = start + timedelta(days=6)
		else:
			stop = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
		return min(stop, self.today)

	def labels(self) -> list[str]:
		"""Short chart labels (``06 Oct`` for weeks, ``Oct 26`` for months)."""
		fmt = "%d %b" if self.kind == "week" else "%b %y"
		return [d.strftime(fmt) for d in self.starts]

	@property
	def first_day(self) -> date:
		return self.starts[0]


def add_months(day: date, months: int) -> date:
	"""First day of the month ``months`` after (or before, if negative) the month of ``day``."""
	index = day.year * 12 + day.month - 1 + months
	return date(index // 12, index % 12 + 1, 1)


def make_buckets(period: str, earliest: date | None, today_: date) -> Buckets:
	"""Buckets for ``period``: 1m (5 weeks), 3m (13 weeks), 6m (26 weeks) or all (from the first activity)."""
	if period in PERIOD_WEEKS:
		last = monday(today_)
		return Buckets(
			"week", [last - timedelta(weeks=n) for n in range(PERIOD_WEEKS[period] - 1, -1, -1)], today_
		)
	first = earliest or today_
	weeks = (monday(today_) - monday(first)).days // 7 + 1
	if weeks <= MAX_WEEKLY_BUCKETS:
		last = monday(today_)
		return Buckets("week", [last - timedelta(weeks=n) for n in range(max(weeks, 4) - 1, -1, -1)], today_)
	months = (today_.year - first.year) * 12 + today_.month - first.month + 1
	months = min(months, MAX_MONTHLY_BUCKETS)
	current = today_.replace(day=1)
	return Buckets("month", [add_months(current, -n) for n in range(months - 1, -1, -1)], today_)


def get_health(project: str, period: str = "3m") -> frappe._dict:
	"""Compute every number of the Project Health dashboard (permission aware through frappe.get_list)."""
	period = period if period in PERIODS else "3m"
	today_ = getdate(today())
	items = frappe.get_list(
		"Work Item",
		filters={"project": project},
		fields=[
			"name",
			"tracker",
			"status",
			"priority",
			"assigned_to",
			"is_closed",
			"creation",
			"closed_on",
			"due_date",
			"estimated_hours",
			"spent_hours",
			"done_percent",
			"sprint",
			"dependent_on_client",
			"client_dependency_since",
		],
		limit_page_length=0,
	)
	entries = frappe.get_list(
		"Time Entry",
		filters={"project": project},
		fields=["date", "hours", "is_billable", "user", "activity_type"],
		limit_page_length=0,
	)
	earliest = min([as_date(i.creation) for i in items] + [as_date(e.date) for e in entries] or [today_])
	buckets = make_buckets(period, earliest, today_)
	# only activity inside the period is charted; open/closed totals always describe the whole project
	flow = ticket_flow(items, buckets)
	time = time_summary(entries, items, buckets)
	workload = workload_summary(items, entries)
	sprints = velocity(project)
	status = overall_status(project, flow, time, today_)
	return deep_dict(
		{
			"period": period,
			"bucket": buckets.kind,
			"labels": buckets.labels(),
			"flow": flow,
			"time": time,
			"workload": workload,
			"velocity": sprints,
			"releases": release_health(project, today_),
			"status": status,
		}
	)


def deep_dict(value):
	"""Convert nested dicts to ``frappe._dict`` (attribute access) while leaving other values alone."""
	if isinstance(value, dict):
		return frappe._dict({k: deep_dict(v) for k, v in value.items()})
	if isinstance(value, list):
		return [deep_dict(v) for v in value]
	return value


def as_date(value) -> date | None:
	"""Convert a date/datetime/str to a date (None stays None)."""
	if not value:
		return None
	return value.date() if isinstance(value, datetime) else getdate(value)


def ticket_flow(items: list, buckets: Buckets) -> dict:
	"""Open vs closed, created vs resolved per week, open-backlog trend, aging, resolution time."""
	starts, today_ = buckets.starts, buckets.today
	created_by_week: dict[date, int] = defaultdict(int)
	resolved_by_week: dict[date, int] = defaultdict(int)
	for item in items:
		created_by_week[buckets.key(as_date(item.creation))] += 1
		if cint(item.is_closed) and item.closed_on:
			resolved_by_week[buckets.key(as_date(item.closed_on))] += 1
	open_items = [i for i in items if not cint(i.is_closed)]
	closed_items = [i for i in items if cint(i.is_closed)]

	def open_at(moment: date) -> int:
		return sum(
			1
			for i in items
			if as_date(i.creation) <= moment
			and (not cint(i.is_closed) or not i.closed_on or as_date(i.closed_on) > moment)
		)

	trend = [open_at(buckets.end(start)) for start in starts]
	ages: dict[str, list[int]] = defaultdict(lambda: [0, 0])
	for item in open_items:
		age = (today_ - as_date(item.creation)).days
		ages[next(text for limit, text in AGE_BUCKETS if age <= limit)][0] += 1
		ages[next(text for limit, text in AGE_BUCKETS if age <= limit)][1] += cint(item.dependent_on_client)
	durations = [(as_date(i.closed_on) - as_date(i.creation)).days for i in closed_items if i.closed_on]
	overdue = sum(1 for i in open_items if i.due_date and getdate(i.due_date) < today_)
	client_open = [i for i in open_items if cint(i.dependent_on_client)]
	overdue_client = sum(1 for i in client_open if i.due_date and getdate(i.due_date) < today_)
	waits = [
		(today_ - as_date(i.client_dependency_since)).days for i in client_open if i.client_dependency_since
	]
	by_tracker: dict[str, list[int]] = defaultdict(
		lambda: [0, 0, 0]
	)  # open with us, closed, open waiting on client
	for item in items:
		if cint(item.is_closed):
			by_tracker[item.tracker][1] += 1
		elif cint(item.dependent_on_client):
			by_tracker[item.tracker][2] += 1
		else:
			by_tracker[item.tracker][0] += 1
	first_day = buckets.first_day
	client_trend = client_wait_trend(items, buckets)
	est_open = sum(flt(i.estimated_hours) for i in open_items)
	est_closed = sum(flt(i.estimated_hours) for i in closed_items)
	last_28 = today_ - timedelta(days=28)
	return {
		"created_4w": sum(1 for i in items if as_date(i.creation) > last_28),
		"resolved_4w": sum(1 for i in closed_items if i.closed_on and as_date(i.closed_on) > last_28),
		"total": len(items),
		"open": len(open_items),
		"closed": len(closed_items),
		"completion_pct": flt(len(closed_items) * 100 / len(items), 1) if items else 0.0,
		"overdue": overdue,
		"overdue_pct": flt(overdue * 100 / len(open_items), 1) if open_items else 0.0,
		# overdue work that is waiting on the client is not the delivery team's delay
		"overdue_client": overdue_client,
		"overdue_delivery": overdue - overdue_client,
		"overdue_delivery_pct": flt((overdue - overdue_client) * 100 / len(open_items), 1)
		if open_items
		else 0.0,
		"client_dependent": len(client_open),
		"client_oldest_days": max(waits) if waits else None,
		"client_avg_days": flt(sum(waits) / len(waits), 1) if waits else None,
		"avg_resolution_days": flt(sum(durations) / len(durations), 1) if durations else None,
		"created": [created_by_week.get(w, 0) for w in starts],
		"resolved": [resolved_by_week.get(w, 0) for w in starts],
		"open_trend": trend,
		"created_total": sum(created_by_week.get(w, 0) for w in starts),
		"resolved_total": sum(resolved_by_week.get(w, 0) for w in starts),
		"aging": [
			{"label": text, "count": ages[text][0], "client": ages[text][1]}
			if text in ages
			else {"label": text, "count": 0, "client": 0}
			for _limit, text in AGE_BUCKETS
		],
		"open_by_priority": count_by(open_items, "priority"),
		"open_by_status": count_by(open_items, "status", ordered_by_status=True),
		"by_tracker": [
			{"label": k, "open": v[0], "closed": v[1], "client": v[2]} for k, v in sorted(by_tracker.items())
		],
		# the part of the numbers that waits on the client
		"client_trend": client_trend,
		"created_waiting": sum(
			1 for i in open_items if cint(i.dependent_on_client) and as_date(i.creation) >= first_day
		),
		"estimated_open_hours": flt(est_open, 2),
		"estimated_closed_hours": flt(est_closed, 2),
	}


def count_by(rows: list, field: str, ordered_by_status: bool = False) -> list[dict]:
	"""[{label, count, client}] for ``field``: ``count`` open tickets of which ``client`` wait on the client."""
	counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
	for row in rows:
		key = row.get(field) or _("(none)")
		counts[key][0] += 1
		counts[key][1] += cint(row.get("dependent_on_client"))
	if ordered_by_status:
		sequence = {
			s.name: s.sequence for s in frappe.get_all("Work Item Status", fields=["name", "sequence"])
		}
		ordered = sorted(counts.items(), key=lambda kv: (sequence.get(kv[0], 10**6), kv[0]))
	else:
		ordered = sorted(counts.items(), key=lambda kv: -kv[1][0])
	return [{"label": k, "count": v[0], "client": v[1]} for k, v in ordered]


def client_wait_trend(items: list, buckets: Buckets) -> list[int]:
	"""Open tickets that were waiting on the client at the end of every bucket (rebuilt from the change history)."""
	flagged = {i.name: i for i in items}
	events: dict[str, list[tuple[date, int]]] = defaultdict(list)
	names = list(flagged)
	for start in range(0, len(names), 500):
		rows = frappe.get_all(
			"Version",
			filters={
				"ref_doctype": "Work Item",
				"docname": ["in", names[start : start + 500]],
				"data": ["like", "%dependent_on_client%"],
			},
			fields=["docname", "data", "creation"],
			order_by="creation asc",
		)
		for row in rows:
			try:
				changes = json.loads(row.data or "{}").get("changed", [])
			except ValueError:
				continue
			for change in changes:
				if change[0] == "dependent_on_client":
					events[row.docname].append((as_date(row.creation), cint(change[2])))
	intervals: list[tuple[date, date | None]] = []
	for name, item in flagged.items():
		created = as_date(item.creation)
		closed = as_date(item.closed_on) if cint(item.is_closed) and item.closed_on else None
		begin: date | None = None
		for when, value in events.get(name, []):
			if value and begin is None:
				begin = when
			elif not value:
				intervals.append((begin or created, min(when, closed) if closed else when))
				begin = None
		if begin is None and cint(item.dependent_on_client) and not events.get(name):
			begin = as_date(item.client_dependency_since) or created  # ticked when the ticket was created
		if begin is None and cint(item.dependent_on_client) and events.get(name) and events[name][0][1] == 0:
			begin = as_date(item.client_dependency_since) or created
		if begin is not None and cint(item.dependent_on_client):
			intervals.append((begin, closed))
	return [
		sum(
			1
			for begin, end in intervals
			if begin <= buckets.end(start) and (end is None or end > buckets.end(start))
		)
		for start in buckets.starts
	]


def time_summary(entries: list, items: list, buckets: Buckets) -> dict:
	"""Spent vs billable hours (total, weekly, by person and activity) against the estimate."""
	starts = buckets.starts
	billable_week: dict[date, float] = defaultdict(float)
	other_week: dict[date, float] = defaultdict(float)
	by_user: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
	by_activity: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
	billable = non_billable = 0.0
	for entry in entries:
		hours, is_billable = flt(entry.hours), bool(cint(entry.is_billable))
		week = buckets.key(as_date(entry.date))
		(billable_week if is_billable else other_week)[week] += hours
		by_user[entry.user][0 if is_billable else 1] += hours
		by_activity[entry.activity_type][0 if is_billable else 1] += hours
		billable += hours if is_billable else 0
		non_billable += 0 if is_billable else hours
	spent = billable + non_billable
	estimated = sum(flt(i.estimated_hours) for i in items)
	names = {
		u.name: u.full_name or u.name
		for u in frappe.get_all(
			"User", filters={"name": ["in", list(by_user) or [""]]}, fields=["name", "full_name"]
		)
	}
	return {
		"spent": flt(spent, 2),
		"billable": flt(billable, 2),
		"non_billable": flt(non_billable, 2),
		"billable_pct": flt(billable * 100 / spent, 1) if spent else 0.0,
		"estimated": flt(estimated, 2),
		"burn_pct": flt(spent * 100 / estimated, 1) if estimated else None,
		"billable_by_week": [flt(billable_week.get(w, 0), 2) for w in starts],
		"non_billable_by_week": [flt(other_week.get(w, 0), 2) for w in starts],
		"by_user": sorted(
			[
				{"user": u, "name": names.get(u, u), "billable": flt(v[0], 2), "non_billable": flt(v[1], 2)}
				for u, v in by_user.items()
			],
			key=lambda r: -(r["billable"] + r["non_billable"]),
		),
		"by_activity": sorted(
			[
				{"label": a, "billable": flt(v[0], 2), "non_billable": flt(v[1], 2)}
				for a, v in by_activity.items()
			],
			key=lambda r: -(r["billable"] + r["non_billable"]),
		),
	}


def workload_summary(items: list, entries: list) -> list[dict]:
	"""Open tickets per assignee."""
	open_items = [i for i in items if not cint(i.is_closed)]
	counts: dict[str, int] = defaultdict(int)
	for item in open_items:
		counts[item.assigned_to or ""] += 1
	names = {
		u.name: u.full_name or u.name
		for u in frappe.get_all(
			"User", filters={"name": ["in", [k for k in counts if k] or [""]]}, fields=["name", "full_name"]
		)
	}
	rows = [
		{"user": k, "name": names.get(k, _("Unassigned")) if k else _("Unassigned"), "open": v}
		for k, v in counts.items()
	]
	return sorted(rows, key=lambda r: -r["open"])[:10]


def velocity(project: str) -> list[dict]:
	"""Closed tickets and estimated hours delivered by every completed sprint, plus the running average."""
	sprints = frappe.get_list(
		"Sprint",
		filters={"project": project, "status": "Completed"},
		fields=["name", "sprint_name", "closed_items", "estimated_hours", "start_date"],
		order_by="start_date asc",
		limit_page_length=0,
	)
	return [
		{"sprint": s.sprint_name, "items": cint(s.closed_items), "hours": flt(s.estimated_hours, 2)}
		for s in sprints
	]


def release_health(project: str, today_: date) -> list[dict]:
	"""Open releases with days left and progress (risk flagged when overdue or late)."""
	rows = frappe.get_list(
		"Release",
		filters={"project": project, "status": ["!=", "Closed"]},
		fields=["name", "release_name", "due_date", "percent_complete", "total_items"],
		order_by="due_date asc",
		limit_page_length=0,
	)
	result = []
	for row in rows:
		days_left = (getdate(row.due_date) - today_).days if row.due_date else None
		pct = flt(row.percent_complete)
		risk = "ok"
		if days_left is not None and pct < 100:
			if days_left < 0:
				risk = "late" if pct < 80 else "risk"  # past due: Off track only when well behind
			elif days_left <= 7 and pct < 80:
				risk = "risk"
		result.append(
			{
				"name": row.name,
				"label": row.release_name,
				"due_date": row.due_date,
				"days_left": days_left,
				"percent": pct,
				"items": cint(row.total_items),
				"risk": risk,
			}
		)
	return result


def overall_status(project: str, flow: dict, time: dict, today_: date) -> dict:
	"""Traffic-light status with the reasons behind it."""
	reasons: list[dict] = []

	def add(level: str, text: str) -> None:
		reasons.append({"level": level, "text": text})

	if not flow["total"]:
		return {"level": "none", "label": _("No data yet"), "score": None, "reasons": []}
	if flow["overdue_delivery_pct"] > 25:
		add(
			"red",
			_("{0}% of open tickets are overdue ({1})").format(
				flow["overdue_delivery_pct"], flow["overdue_delivery"]
			),
		)
	elif flow["overdue_delivery_pct"] > 10:
		add(
			"amber",
			_("{0}% of open tickets are overdue ({1})").format(
				flow["overdue_delivery_pct"], flow["overdue_delivery"]
			),
		)
	sprint = frappe.db.get_value("Sprint", {"project": project, "status": "Active"}, "name")
	if sprint:
		rows = [r for r in get_burndown(sprint)["rows"] if r["actual"] is not None]
		scope = get_burndown(sprint)["total"]
		if rows and scope:
			gap = (rows[-1]["actual"] - rows[-1]["ideal"]) / scope
			if gap > 0.25:
				add("red", _("Active sprint is well behind the ideal burndown"))
			elif gap > 0.10:
				add("amber", _("Active sprint is slightly behind the ideal burndown"))
	if time["burn_pct"] is not None:
		done_share = flow["estimated_closed_hours"] * 100 / time["estimated"] if time["estimated"] else 0
		if time["burn_pct"] > 100:
			add("red", _("Spent hours exceed the estimate ({0}%)").format(time["burn_pct"]))
		elif time["burn_pct"] - done_share > 25:
			add(
				"amber",
				_("Effort used ({0}%) is ahead of work completed ({1}%)").format(
					time["burn_pct"], flt(done_share, 0)
				),
			)
	for release in release_health(project, today_):
		if release["risk"] == "late":
			add(
				"red",
				_("Release {0} is past its due date at {1}%").format(
					release["label"], flt(release["percent"], 0)
				),
			)
		elif release["risk"] == "risk":
			add(
				"amber",
				_("Release {0} is at {1}% and close to or just past its due date").format(
					release["label"], flt(release["percent"], 0)
				),
			)
	if flow["created_4w"] > flow["resolved_4w"] * 1.5 and flow["created_4w"] >= 4:
		add("amber", _("The backlog grew over the last 4 weeks (more created than resolved)"))
	if flow["client_dependent"]:  # informational: shown, but neither the level nor the score changes
		add(
			"info",
			_("{0} tickets are waiting on the client (oldest {1} days)").format(
				flow["client_dependent"], flow["client_oldest_days"] or 0
			),
		)
	level = (
		"red"
		if any(r["level"] == "red" for r in reasons)
		else "amber"
		if any(r["level"] == "amber" for r in reasons)
		else "green"
	)
	score = max(
		0,
		100
		- 25 * sum(r["level"] == "red" for r in reasons)
		- 10 * sum(r["level"] == "amber" for r in reasons),
	)
	label_ = {"green": _("On track"), "amber": _("At risk"), "red": _("Off track")}[level]
	if level == "green":
		add("green", _("No schedule, effort or backlog risks detected"))
	return {"level": level, "label": label_, "score": score, "reasons": reasons}
