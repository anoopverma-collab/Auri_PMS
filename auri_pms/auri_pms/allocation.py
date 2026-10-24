"""Allocation vs utilisation of a project's team: hours planned per person against hours logged."""

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe.utils import add_days, cint, flt, getdate, today

from auri_pms.auri_pms.utils import setting


def positive_setting(fieldname: str) -> int:
	"""A PMS Settings number that must be above 0; 0 or empty (a settings form saved before the field
	existed) falls back to the field default."""
	return cint(setting(fieldname)) or cint(frappe.get_meta("PMS Settings").get_field(fieldname).default)


def utilisation_window(today_=None) -> tuple:
	"""First and last day of the utilisation window (PMS Settings), and its length in weeks."""
	end = getdate(today_ or today())
	weeks = max(1, positive_setting("utilisation_window_weeks"))
	return add_days(end, -(weeks * 7) + 1), end, weeks


def utilisation_state(pct: float | None, over: int, under: int) -> str:
	"""``over`` / ``under`` / ``ok`` against the PMS Settings limits; ``none`` when nothing is allocated."""
	if pct is None:
		return "none"
	return "over" if pct > over else "under" if pct < under else "ok"


def project_allocation(project: str, today_=None) -> dict:
	"""Allocated vs logged hours per week for the current members of ``project``.

	Allocation is a share of the weekly capacity in PMS Settings; logged hours are averaged over the
	utilisation window and also given week by week. People who logged time but are no longer members
	are left out; their hours are only reported as a total. Allocation across projects is on the
	Portfolio (``team_capacity``).
	"""
	capacity = flt(setting("weekly_capacity_hours")) or 40.0
	over, under = positive_setting("over_utilisation_pct"), positive_setting("under_utilisation_pct")
	start, end, weeks = utilisation_window(today_)
	members = frappe.get_all(
		"Project Member",
		filters={"parent": project, "parenttype": "Project"},
		fields=["user", "full_name", "project_role", "allocation_pct"],
		order_by="idx asc",
	)
	people = {m.user: m for m in members}
	week_of = lambda day: min(weeks - 1, (getdate(day) - start).days // 7)  # noqa: E731
	by_week: dict[str, list[float]] = defaultdict(lambda: [0.0] * weeks)
	former = 0.0
	for entry in frappe.get_all(
		"Time Entry",
		filters={"project": project, "date": ["between", [start, end]]},
		fields=["user", "hours", "date"],
	):
		if entry.user in people:
			by_week[entry.user][week_of(entry.date)] += flt(entry.hours)
		else:
			former += flt(entry.hours)

	names = {
		u.name: u.full_name or u.name
		for u in frappe.get_all(
			"User", filters={"name": ["in", list(people) or [""]]}, fields=["name", "full_name"]
		)
	}
	rows = []
	for user, member in people.items():
		allocated = flt(member.allocation_pct) * capacity / 100
		weekly = by_week[user]
		per_week = sum(weekly) / weeks
		pct = flt(per_week * 100 / allocated, 0) if allocated else None
		row = {
			"user": user,
			"name": names.get(user) or member.full_name or user,
			"role": member.project_role,
			"allocation_pct": flt(member.allocation_pct, 0),
			"allocated_week": flt(allocated, 1),
			"logged_week": flt(per_week, 1),
			"weekly": [flt(h, 1) for h in weekly],
			"utilisation_pct": pct,
			"state": utilisation_state(pct, over, under),
		}
		rows.append(row)
	rows.sort(key=lambda r: (r["utilisation_pct"] is None, -(r["utilisation_pct"] or 0), r["name"]))

	allocated_week = sum(r["allocated_week"] for r in rows)
	team_weekly = [sum(r["weekly"][w] for r in rows) for w in range(weeks)]
	logged_week = sum(team_weekly) / weeks
	pct = flt(logged_week * 100 / allocated_week, 0) if allocated_week else None
	return {
		"capacity": capacity,
		"weeks": weeks,
		"from_date": str(start),
		"to_date": str(end),
		"week_starts": [str(add_days(start, 7 * w)) for w in range(weeks)],
		"over_pct": over,
		"under_pct": under,
		"members": rows,
		"allocated_week": flt(allocated_week, 1),
		"logged_week": flt(logged_week, 1),
		"team_weekly": [flt(h, 1) for h in team_weekly],
		"former_logged_week": flt(former / weeks, 1),
		"utilisation_pct": pct,
		"state": utilisation_state(pct, over, under),
		"counts": {s: sum(r["state"] == s for r in rows) for s in ("over", "ok", "under", "none")},
	}


def team_capacity(projects: dict[str, str], today_=None) -> dict:
	"""Every member's allocation split across ``projects`` ({name: label}) against 100% of their week.

	Logged hours are averaged over the utilisation window and only count time on ``projects``, so a
	viewer sees nothing about projects they cannot open. Flags people allocated above 100% and people
	logging more than the over-utilised limit of their weekly capacity (burnout risk). ``member_of`` lists the
	projects each person is a member of, which is what the Portfolio filters the team by.
	"""
	capacity = flt(setting("weekly_capacity_hours")) or 40.0
	over, under = positive_setting("over_utilisation_pct"), positive_setting("under_utilisation_pct")
	start, end, weeks = utilisation_window(today_)
	names = list(projects) or [""]
	split: dict[str, dict[str, float]] = defaultdict(dict)
	for row in frappe.get_all(
		"Project Member",
		filters={"parenttype": "Project", "parent": ["in", names]},
		fields=["user", "parent", "allocation_pct"],
	):
		split[row.user][row.parent] = flt(row.allocation_pct)
	logged: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
	for entry in frappe.get_all(
		"Time Entry",
		filters={"project": ["in", names], "date": ["between", [start, end]]},
		fields=["user", "project", "hours"],
	):
		if entry.user in split:  # only people still on one of the teams
			logged[entry.user][entry.project] += flt(entry.hours)
	people = list(split)  # every current member of the projects, allocated or not
	full = {
		u.name: u.full_name or u.name
		for u in frappe.get_all(
			"User", filters={"name": ["in", people or [""]], "enabled": 1}, fields=["name", "full_name"]
		)
	}
	rows = []
	for user in people:
		if user not in full:
			continue
		total = sum(split[user].values())
		per_week = sum(logged[user].values()) / weeks
		allocated = total * capacity / 100
		pct = flt(per_week * 100 / allocated, 0) if allocated else None
		rows.append(
			{
				"user": user,
				"name": full[user],
				"projects": sorted(
					(
						{
							"project": p,
							"label": projects[p],
							"pct": flt(split[user].get(p), 0),
							"logged_week": flt(logged[user].get(p, 0) / weeks, 1),
						}
						for p in set(split[user]) | set(logged[user])
						if split[user].get(p) or logged[user].get(p)
					),
					key=lambda x: (-x["pct"], x["label"]),
				),
				"member_of": sorted(split[user]),
				"total_pct": flt(total, 0),
				"allocated_week": flt(allocated, 1),
				"logged_week": flt(per_week, 1),
				"utilisation_pct": pct,
				"state": utilisation_state(pct, over, under),
				"over_allocated": total > 100,
				"burnout": per_week > capacity * over / 100,
			}
		)
	rows.sort(key=lambda r: (-r["total_pct"], -r["logged_week"], r["name"]))
	return {
		"capacity": capacity,
		"weeks": weeks,
		"people": rows,
		"over_allocated": sum(r["over_allocated"] for r in rows),
		"burnout": sum(r["burnout"] for r in rows),
		"spare_week": flt(sum(max(0.0, 100 - r["total_pct"]) * capacity / 100 for r in rows), 1),
		"avg_allocation_pct": flt(sum(r["total_pct"] for r in rows) / len(rows), 0) if rows else 0,
	}


def project_team(project: str, visible: list[str] | set[str]) -> dict:
	"""The members of ``project`` with their load across every project the viewer can see (plus this one).

	Burnout and over-allocation are about a person's whole week, so their other projects count when the viewer
	may see them; a viewer who sees only this project gets the load on it."""
	labels = {
		p.name: p.project_name or p.name
		for p in frappe.get_all(
			"Project", filters={"name": ["in", [*visible, project]]}, fields=["name", "project_name"]
		)
	}
	data = team_capacity(labels)
	data["people"] = [m for m in data["people"] if project in m["member_of"]]
	data["over_allocated"] = sum(m["over_allocated"] for m in data["people"])
	data["burnout"] = sum(m["burnout"] for m in data["people"])
	return data
