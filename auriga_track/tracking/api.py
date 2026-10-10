"""Whitelisted API of Auri PMS (spec 5 R-18, section 6)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from auriga_track.permissions import can_see_project
from auriga_track.tracking.utils import (
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
		else frappe.get_all("Tracker", {"is_active": 1}, pluck="name")
	)
	return [
		[n]
		for n in frappe.get_all(
			"Tracker",
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
	work_item: str, hours: float, activity_type: str, date: str | None = None, comment: str | None = None
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
