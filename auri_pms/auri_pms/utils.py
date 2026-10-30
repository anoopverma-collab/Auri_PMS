"""Shared helpers for Auri PMS: capability lookup, hierarchy walking, rollups and progress."""

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cint, flt

CAPABILITY_FIELDS: tuple[str, ...] = (
	"can_create_items",
	"can_edit_any_item",
	"can_delete_items",
	"can_manage_releases",
	"can_manage_categories",
	"can_log_time",
	"can_edit_others_time",
	"can_manage_members",
	"can_be_assigned",
	"can_see_all_items",
)
# Full access to every project. Auri PMS Manager is not here: a Manager works like a member and sees only the projects they are on.
ADMIN_ROLES = frozenset({"Auri PMS Admin", "System Manager"})
# ERPNext roles that already have their own view of every Project; Project visibility is not narrowed for them.
ERPNEXT_PROJECT_ROLES = frozenset({"Projects Manager", "Projects User"})


# --------------------------------------------------------------------------- request cache
def _cache() -> dict:
	"""Return the per-request cache dict kept on ``frappe.local``."""
	if not hasattr(frappe.local, "track_cache"):
		frappe.local.track_cache = {}
	return frappe.local.track_cache


def clear_cache(doc=None, method: str | None = None) -> None:
	"""Drop the per-request capability cache. Usable directly or as a doc_events hook."""
	frappe.local.track_cache = {}


# --------------------------------------------------------------------------- users and roles
def ensure_pms_project(project: str | None, action: str) -> None:
	"""Throw unless ``project`` has Enable Auri PMS ticked (``action`` completes "before ...")."""
	if project and not cint(frappe.db.get_value("Project", project, "pms_enabled")):
		frappe.throw(_("Enable Auri PMS on Project {0} before {1}").format(project, action))


def is_admin(user: str | None = None) -> bool:
	"""Return True for Administrator, Auri PMS Admin and System Manager (they see and do everything)."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(ADMIN_ROLES & set(frappe.get_roles(user)))


def is_user_enabled(user: str) -> bool:
	"""Return True if the User exists and is enabled."""
	if user == "Administrator":
		return True
	key = ("enabled", user)
	cache = _cache()
	if key not in cache:
		cache[key] = bool(cint(frappe.db.get_value("User", user, "enabled")))
	return cache[key]


def has_unrestricted_project_view(user: str) -> bool:
	"""True if the user sees every Project (Auri PMS and system admins and ERPNext project roles)."""
	return is_admin(user) or bool((ERPNEXT_PROJECT_ROLES) & set(frappe.get_roles(user)))


def ignore_company_restrictions() -> bool:
	"""PMS Settings > Auri PMS Projects Ignore Company Restrictions. A site that never saved the setting keeps it ticked.

	A Check that was never saved reads as 0 through the settings document, so the stored row is looked at itself:
	no row means the field default (ticked)."""
	row = frappe.db.sql(
		"select value from `tabSingles` where doctype = 'PMS Settings' and field = 'projects_ignore_company_restrictions'"
	)
	return True if not row else bool(cint(row[0][0]))


def pms_project_rows(filters: dict | None = None, **kwargs) -> list:
	"""Project rows for the Auri PMS screens: like ``frappe.get_list``, but with *Auri PMS Projects Ignore Company
	Restrictions* ticked the rows are the projects the person belongs to (or that are public), not what a Company
	User Permission leaves of them. An admin, or someone with an ERPNext project role, sees every project as before."""
	if not ignore_company_restrictions():
		return frappe.get_list("Project", filters=filters, **kwargs)
	user = frappe.session.user
	filters = dict(filters or {})
	if not has_unrestricted_project_view(user):
		if not is_user_enabled(user):
			return []
		visible = set(
			frappe.get_all("Project Member", filters={"parenttype": "Project", "user": user}, pluck="parent")
		) | set(frappe.get_all("Project", filters={"is_public": 1}, pluck="name"))
		existing = filters.get("name")
		if isinstance(existing, (list, tuple)) and len(existing) == 2 and existing[0] == "in":
			visible &= set(existing[1])
		filters["name"] = ["in", sorted(visible) or [""]]
	return frappe.get_all("Project", filters=filters, **kwargs)


def portfolio_projects(user: str | None = None) -> list[str]:
	"""Projects whose figures ``user`` sees on Delivery & Health (the Portfolio).

	Auri PMS Admins and System Managers see every project with Auri PMS switched on. Anyone else (an Auri PMS
	Manager or Auri PMS User) sees the projects they are a member of, whatever their Project Role; an empty list
	means no Delivery & Health at all.
	"""
	user = user or frappe.session.user
	enabled = frappe.get_all("Project", filters={"pms_enabled": 1}, pluck="name", order_by="name")
	if is_admin(user):
		return enabled
	if not is_user_enabled(user):
		return []
	mine = set(
		frappe.get_all(
			"Project Member",
			filters={"parenttype": "Project", "user": user, "parent": ["in", enabled or [""]]},
			pluck="parent",
		)
	)
	return [p for p in enabled if p in mine]


def managed_projects(user: str | None = None) -> list[str]:
	"""Projects ``user`` manages: every project for an admin, otherwise those where their Project Role can manage members.

	Notes on a project and its team workload are for these people, not for every member."""
	user = user or frappe.session.user
	enabled = portfolio_projects(user)
	if is_admin(user) or not enabled:
		return enabled
	managing_roles = set(frappe.get_all("Project Role", filters={"can_manage_members": 1}, pluck="name"))
	mine = {
		m.parent
		for m in frappe.get_all(
			"Project Member",
			filters={"parenttype": "Project", "user": user, "parent": ["in", enabled]},
			fields=["parent", "project_role"],
		)
		if m.project_role in managing_roles
	}
	return [p for p in enabled if p in mine]


# --------------------------------------------------------------------------- settings
def get_settings():
	"""Return the cached PMS Settings document."""
	return frappe.get_cached_doc("PMS Settings")


def setting(fieldname: str):
	"""A PMS Settings value; a threshold never saved (new install) falls back to the field default."""
	value = get_settings().get(fieldname)
	if value in (None, ""):
		value = frappe.get_meta("PMS Settings").get_field(fieldname).default
	return value


# --------------------------------------------------------------------------- capabilities
def _role_flags(role: str | None) -> dict:
	"""Return the capability flags of a Project Role (all False when the role is missing)."""
	if not role:
		return dict.fromkeys(CAPABILITY_FIELDS, False)
	key = ("role_flags", role)
	cache = _cache()
	if key not in cache:
		row = frappe.db.get_value("Project Role", role, list(CAPABILITY_FIELDS), as_dict=True) or {}
		cache[key] = {f: bool(cint(row.get(f))) for f in CAPABILITY_FIELDS}
	return dict(cache[key])


def get_member_role(project: str, user: str) -> str | None:
	"""Return the Project Role of ``user`` as a member of ``project`` (None if not a member)."""
	key = ("member_role", project, user)
	cache = _cache()
	if key not in cache:
		cache[key] = frappe.db.get_value(
			"Project Member", {"parent": project, "parenttype": "Project", "user": user}, "project_role"
		)
	return cache[key]


def get_project_role(project: str, user: str | None = None) -> str | None:
	"""Return the effective Project Role: member role, else the public role on a public project, else None."""
	user = user or frappe.session.user
	role = get_member_role(project, user)
	if role:
		return role
	if cint(frappe.db.get_value("Project", project, "is_public")):
		return get_settings().public_project_role
	return None


def get_capabilities(project: str, user: str | None = None, members_only: bool = False) -> dict:
	"""Return the Project Role flags for ``user`` on ``project``.

	Auri PMS Admin/System Manager -> all True. Member (any Auri PMS role) -> their Project Role's flags.
	A non-member (a public project included) -> all False: a public project is read-only for them.
	Otherwise -> all False. Disabled users always get all False. Cached per request.

	With ``members_only`` the admin shortcut and the public-project fallback are skipped, so only
	real members are reported (used to decide who may be assigned work).
	"""
	user = user or frappe.session.user
	key = ("caps", project, user, members_only)
	cache = _cache()
	if key in cache:
		return dict(cache[key])

	if not project or not is_user_enabled(user):
		caps = dict.fromkeys(CAPABILITY_FIELDS, False)
	elif not members_only and is_admin(user):
		caps = dict.fromkeys(CAPABILITY_FIELDS, True)
	else:
		# Only an allocated member can change anything: a public project is read-only for everyone else.
		caps = _role_flags(get_member_role(project, user))

	cache[key] = caps
	return dict(caps)


def get_view_only_fields(project: str, user: str | None = None) -> set[str]:
	"""Return the Work Item fields ``user`` may only view on ``project`` (Project Role > Field Rules).

	Admins, non-members and disabled users get none here: they are handled by the capability checks."""
	user = user or frappe.session.user
	if not project or is_admin(user) or not is_user_enabled(user):
		return set()
	role = get_member_role(project, user)
	if not role:
		return set()
	key = ("view_only", role)
	cache = _cache()
	if key not in cache:
		cache[key] = set(
			frappe.get_all(
				"Project Role Field Rule",
				filters={"parent": role, "parenttype": "Project Role", "can_edit": 0},
				pluck="field_name",
			)
		)
	return set(cache[key])


def is_allocated(project: str | None, user: str | None = None) -> bool:
	"""True when ``user`` may change data of ``project``: an Auri PMS Admin / System Manager or a member of the project."""
	user = user or frappe.session.user
	if is_admin(user):
		return True
	return bool(project and is_user_enabled(user) and get_member_role(project, user))


def has_capability(project: str, capability: str, user: str | None = None) -> bool:
	"""Shortcut for ``get_capabilities(project, user)[capability]``."""
	return bool(get_capabilities(project, user).get(capability))


# Who may create each doctype: the Project Role capability needed on at least one project. "admin" = only Auri PMS Admins
# and System Managers (system generated records); "modules" = can_manage_modules. The New button and the menu shortcuts
# follow this table; each record still checks the capability on its own project when it is saved.
CREATE_RULES: dict[str, str] = {
	"Work Item": "can_create_items",
	"Time Entry": "can_log_time",
	"Risk Register": "can_create_items",
	"Sprint": "can_manage_releases",
	"Release": "can_manage_releases",
	"Work Item Category": "can_manage_categories",
	"Project Module": "modules",
	"Project Status Report": "admin",
	"Project Dashboard Snapshot": "admin",
}


def can_create_doctype(doctype: str, user: str | None = None) -> bool:
	"""Return True when ``user`` may create ``doctype`` on some project (see ``CREATE_RULES``); unlisted doctypes: True."""
	user = user or frappe.session.user
	rule = CREATE_RULES.get(doctype)
	if rule is None or is_admin(user):
		return True
	if rule == "admin":
		return False
	if rule == "modules":
		return can_manage_modules(user)
	if not rule.startswith("can_"):
		return False
	roles = frappe.get_all("Project Role", filters={rule: 1}, pluck="name")
	if not roles:
		return False
	return bool(
		frappe.db.exists(
			"Project Member", {"parenttype": "Project", "user": user, "project_role": ["in", roles]}
		)
	)


def create_permissions(user: str | None = None) -> dict[str, bool]:
	"""{doctype: may create} for every doctype of ``CREATE_RULES``, sent to the browser at login."""
	return {doctype: can_create_doctype(doctype, user) for doctype in CREATE_RULES}


def can_manage_modules(user: str | None = None) -> bool:
	"""Return True when ``user`` may create or change the shared Project Modules.

	Admins and Auri PMS Managers always may; so may a member whose Project Role on any project can manage categories."""
	user = user or frappe.session.user
	if is_admin(user) or "Auri PMS Manager" in frappe.get_roles(user):
		return True
	return bool(
		frappe.db.sql(
			"""
			select 1
			from `tabProject Member` pm
			join `tabProject Role` pr on pr.name = pm.project_role and pr.can_manage_categories = 1
			where pm.parenttype = 'Project' and pm.user = %s
			limit 1
			""",
			user,
		)
	)


# --------------------------------------------------------------------------- hierarchy
def get_ancestors(work_item: str | None) -> list[str]:
	"""Return the ancestor chain of ``work_item``, nearest parent first (cycle safe)."""
	chain: list[str] = []
	seen = {work_item}
	parent = work_item
	while parent:
		parent = frappe.db.get_value("Work Item", parent, "parent_work_item")
		if not parent or parent in seen:
			break
		chain.append(parent)
		seen.add(parent)
	return chain


def get_children(work_item: str) -> list[str]:
	"""Return the names of the direct children of ``work_item``."""
	return frappe.get_all("Work Item", filters={"parent_work_item": work_item}, pluck="name")


def get_subtree_height(work_item: str) -> int:
	"""Return how many levels exist below ``work_item`` (0 for a leaf)."""
	height = 0
	level = [work_item]
	seen = {work_item}
	while level:
		children = frappe.get_all("Work Item", filters={"parent_work_item": ["in", level]}, pluck="name")
		level = [c for c in children if c not in seen]
		seen.update(level)
		if level:
			height += 1
	return height


def get_descendants(work_item: str) -> list[str]:
	"""Return every descendant of ``work_item``."""
	found: list[str] = []
	level = [work_item]
	seen = {work_item}
	while level:
		children = frappe.get_all("Work Item", filters={"parent_work_item": ["in", level]}, pluck="name")
		level = [c for c in children if c not in seen]
		seen.update(level)
		found.extend(level)
	return found


# --------------------------------------------------------------------------- progress (R-32)
def compute_progress(items: list[dict]) -> float:
	"""Progress of a set of items (R-32).

	Each item counts 100 if closed, else its ``done_percent``. If every item has ``hours`` > 0 the
	average is weighted by hours, otherwise it is a simple average. An empty set is 0.
	"""
	if not items:
		return 0.0
	values = [100.0 if cint(i.get("is_closed")) else flt(i.get("done_percent")) for i in items]
	weights = [flt(i.get("hours")) for i in items]
	if all(w > 0 for w in weights):
		return flt(sum(v * w for v, w in zip(values, weights, strict=True)) / sum(weights), 2)
	return flt(sum(values) / len(values), 2)


# --------------------------------------------------------------------------- rollups (R-28 .. R-33)
def recalc_work_item(name: str) -> None:
	"""Recompute spent/estimated totals and (for parents) % done of one Work Item (R-28, R-29, R-31)."""
	if not name or not frappe.db.exists("Work Item", name):
		return
	own_spent = flt(
		frappe.db.sql("select coalesce(sum(hours), 0) from `tabTime Entry` where work_item = %s", name)[0][0]
	)
	own_est = flt(frappe.db.get_value("Work Item", name, "estimated_hours"))
	children = frappe.get_all(
		"Work Item",
		filters={"parent_work_item": name},
		fields=["is_closed", "done_percent", "estimated_hours", "total_estimated_hours", "total_spent_hours"],
	)
	values = {
		"spent_hours": own_spent,
		"total_spent_hours": own_spent + sum(flt(c.total_spent_hours) for c in children),
		"total_estimated_hours": own_est + sum(flt(c.total_estimated_hours) for c in children),
	}
	if children:
		values["done_percent"] = compute_progress(
			[
				{
					"is_closed": c.is_closed,
					"done_percent": c.done_percent,
					"hours": c.total_estimated_hours,
				}
				for c in children
			]
		)
	frappe.db.set_value("Work Item", name, values, update_modified=False)


def recalc_chain(name: str | None) -> None:
	"""Recompute ``name`` and every ancestor, bottom-up (R-30)."""
	if not name:
		return
	for item in [name, *get_ancestors(name)]:
		recalc_work_item(item)


def recalc_release(release: str | None) -> None:
	"""Recompute the roll-up fields of a Release (R-33)."""
	if not release or not frappe.db.exists("Release", release):
		return
	items = frappe.get_all(
		"Work Item",
		filters={"release": release},
		fields=["is_closed", "done_percent", "estimated_hours", "spent_hours", "tracker"],
	)
	roadmap = {
		t.name: cint(t.show_in_roadmap)
		for t in frappe.get_all("Ticket Type", fields=["name", "show_in_roadmap"])
	}
	progress_items = [
		{"is_closed": i.is_closed, "done_percent": i.done_percent, "hours": i.estimated_hours}
		for i in items
		if roadmap.get(i.tracker, 1)
	]
	frappe.db.set_value(
		"Release",
		release,
		{
			"total_items": len(items),
			"closed_items": sum(1 for i in items if cint(i.is_closed)),
			"estimated_hours": sum(flt(i.estimated_hours) for i in items),
			"spent_hours": sum(flt(i.spent_hours) for i in items),
			"percent_complete": compute_progress(progress_items),
		},
		update_modified=False,
	)


# --------------------------------------------------------------------------- workflow (R-17, R-18)
def transition_allowed(
	tracker: str, from_status: str, to_status: str, project: str, user: str | None = None
) -> bool:
	"""Return True if ``user`` may move an item of ``tracker`` from one status to another on ``project``.

	An empty transition table allows every move; Tracker/System Managers bypass the table.
	"""
	user = user or frappe.session.user
	if from_status == to_status or is_admin(user):
		return True
	rows = frappe.get_all(
		"Ticket Type Transition",
		filters={"parent": tracker, "parenttype": "Ticket Type", "parentfield": "transitions"},
		fields=["from_status", "to_status", "project_role"],
	)
	if not rows:
		return True
	role = get_project_role(project, user)
	return any(
		r.from_status == from_status
		and r.to_status == to_status
		and (not r.project_role or r.project_role == role)
		for r in rows
	)


def get_enabled_trackers(project: str) -> list[str]:
	"""Return the trackers enabled on ``project``; an empty list on the project means all active trackers."""
	enabled = frappe.get_all(
		"Project Ticket Type",
		filters={"parent": project, "parenttype": "Project", "parentfield": "enabled_trackers"},
		pluck="tracker",
	)
	if enabled:
		return enabled
	return frappe.get_all("Ticket Type", filters={"is_active": 1}, pluck="name")


def get_parent_scope(project: str) -> list[str]:
	"""Return the projects a work item of ``project`` may take its parent from: the project and its parent project."""
	parent = frappe.db.get_value("Project", project, "parent_project")
	return [project, parent] if parent else [project]


def get_enabled_modules(project: str) -> list[str]:
	"""Return the Project Modules tagged on ``project`` (Enabled Modules); only these are offered on its work items."""
	return frappe.get_all(
		"Project Enabled Module",
		filters={"parent": project, "parenttype": "Project", "parentfield": "enabled_modules"},
		pluck="module",
	)


def get_enabled_statuses(project: str) -> list[str]:
	"""Return the statuses set on ``project`` (Enabled Statuses); only these are offered on its work items."""
	return frappe.get_all(
		"Project Work Item Status",
		filters={"parent": project, "parenttype": "Project", "parentfield": "enabled_statuses"},
		pluck="status",
	)


def follow_work_item(work_item: str, user: str | None) -> None:
	"""Make ``user`` a watcher (Document Follow) of ``work_item``; idempotent."""
	if not user or user in ("Administrator", "Guest") or not is_user_enabled(user):
		return
	filters = {"ref_doctype": "Work Item", "ref_docname": work_item, "user": user}
	if not frappe.db.exists("Document Follow", filters):
		frappe.get_doc({"doctype": "Document Follow", **filters}).insert(ignore_permissions=True)


def list_target(doctype: str, filters: dict) -> dict:
	"""Where a dashboard line leads: the list of ``doctype`` with these filters."""
	return {"route": ["List", doctype, "List"], "filters": filters}


def form_target(doctype: str, name: str) -> dict:
	"""Where a dashboard line leads: one record."""
	return {"route": ["Form", doctype, name], "filters": {}}


def report_target(report: str, filters: dict) -> dict:
	"""Where a dashboard line leads: a query report with these filters."""
	return {"route": ["query-report", report], "filters": filters}


def summary_card(value, label: str, datatype: str = "Int", indicator: str | None = None) -> dict:
	"""One figure of a query report's summary row; ``indicator`` is Red, Orange, Green, Blue or Gray."""
	card = {"value": value, "label": label, "datatype": datatype}
	if indicator:
		card["indicator"] = indicator
	return card


def safe_sendmail(**kwargs) -> bool:
	"""Queue an email without ever blocking the caller; failures are logged. Returns True if queued.

	``frappe.sendmail`` reports a missing outgoing account with ``frappe.throw``, which also pushes a popup
	message for the user. That message is dropped here, because a status change must not look like it failed.
	"""
	message_count = len(getattr(frappe.local, "message_log", None) or [])
	try:
		frappe.sendmail(**kwargs)
		return True
	except Exception:
		del frappe.local.message_log[message_count:]
		frappe.log_error(title="Auri PMS: email could not be queued")
		return False


# --------------------------------------------------------------------------- sprints
def recalc_sprint(sprint: str | None) -> None:
	"""Recompute the roll-up fields of a Sprint from the items currently in it."""
	if not sprint or not frappe.db.exists("Sprint", sprint):
		return
	items = frappe.get_all(
		"Work Item",
		filters={"sprint": sprint},
		fields=["is_closed", "done_percent", "estimated_hours", "spent_hours"],
	)
	frappe.db.set_value(
		"Sprint",
		sprint,
		{
			"total_items": len(items),
			"closed_items": sum(1 for i in items if cint(i.is_closed)),
			"estimated_hours": sum(flt(i.estimated_hours) for i in items),
			"spent_hours": sum(flt(i.spent_hours) for i in items),
			"percent_complete": compute_progress(
				[
					{"is_closed": i.is_closed, "done_percent": i.done_percent, "hours": i.estimated_hours}
					for i in items
				]
			),
		},
		update_modified=False,
	)


def get_burndown(sprint: str, as_of: str | None = None) -> dict:
	"""Remaining work per day of a sprint against the ideal line.

	Scope is the items currently in the sprint, measured in estimated hours (or item count when nothing
	is estimated). An item counts as burned on the day it was closed. ``actual`` stops at ``as_of``/today.
	"""
	from frappe.utils import add_days, date_diff, getdate, today

	sprint_doc = frappe.db.get_value("Sprint", sprint, ["start_date", "end_date", "status"], as_dict=True)
	start, end = getdate(sprint_doc.start_date), getdate(sprint_doc.end_date)
	items = frappe.get_all(
		"Work Item",
		filters={"sprint": sprint},
		fields=["estimated_hours", "is_closed", "closed_on"],
	)
	use_hours = any(flt(i.estimated_hours) > 0 for i in items)
	weight = lambda item: flt(item.estimated_hours) if use_hours else 1  # noqa: E731
	total = sum(weight(i) for i in items)
	cutoff = getdate(as_of) if as_of else getdate(today())
	if sprint_doc.status == "Completed":
		cutoff = end
	days = date_diff(end, start)
	rows = []
	for offset in range(days + 1):
		day = getdate(add_days(start, offset))
		burned_today = sum(
			weight(i) for i in items if cint(i.is_closed) and i.closed_on and getdate(i.closed_on) == day
		)
		burned_by_day = sum(
			weight(i) for i in items if cint(i.is_closed) and i.closed_on and getdate(i.closed_on) <= day
		)
		rows.append(
			{
				"date": day,
				"ideal": flt(total - total * offset / days, 2) if days else 0.0,
				"actual": flt(total - burned_by_day, 2) if day <= cutoff else None,
				"completed": flt(burned_today, 2),
			}
		)
	return {"unit": "hours" if use_hours else "items", "total": flt(total, 2), "rows": rows}


# --------------------------------------------------------------------------- status colours
INDICATOR_PALETTE = {
	"blue": "#2490ef",
	"cyan": "#00b8d9",
	"green": "#22c55e",
	"orange": "#ff9f1c",
	"yellow": "#facc15",
	"red": "#e24c4c",
	"purple": "#8b5cf6",
	"pink": "#ec4899",
	"gray": "#8d99a6",
}


def nearest_indicator(hex_color: str | None) -> str:
	"""Map a status colour (hex) to the nearest Desk indicator colour name; gray when unset or invalid."""
	if not hex_color or not re.fullmatch(r"#[0-9a-fA-F]{6}", hex_color):
		return "gray"

	def rgb(value: str) -> tuple[int, ...]:
		return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))

	target = rgb(hex_color)
	return min(
		INDICATOR_PALETTE,
		key=lambda name: sum((a - b) ** 2 for a, b in zip(rgb(INDICATOR_PALETTE[name]), target, strict=True)),
	)


def linked_tickets(field: str, name: str) -> dict:
	"""The Work Items whose ``field`` (release or sprint) is ``name``: counts per status and person, plus the tickets.

	Uses get_list, so only the tickets of projects the user may see come back.
	"""
	rows = frappe.get_list(
		"Work Item",
		filters={field: name},
		fields=[
			"name",
			"subject",
			"status",
			"priority",
			"assigned_to",
			"due_date",
			"is_closed",
			"estimated_hours",
			"spent_hours",
			"done_percent",
			"sprint",
			"release",
		],
		order_by="is_closed asc, due_date asc, name asc",
		limit_page_length=0,
	)
	users = [r.assigned_to for r in rows if r.assigned_to]
	names = {
		u.name: u.full_name or u.name
		for u in frappe.get_all("User", filters={"name": ["in", users or [""]]}, fields=["name", "full_name"])
	}
	statuses: dict[str, int] = {}
	people: dict[str, int] = {}
	for row in rows:
		statuses[row.status] = statuses.get(row.status, 0) + 1
		if not row.is_closed:
			people[row.assigned_to or ""] = people.get(row.assigned_to or "", 0) + 1
		row["assignee"] = names.get(row.assigned_to) or (row.assigned_to or "")
	return {
		"total": len(rows),
		"closed": sum(1 for r in rows if r.is_closed),
		"statuses": statuses,
		"open_by_person": [
			{"user": u, "name": names.get(u) or _("Unassigned"), "open": n}
			for u, n in sorted(people.items(), key=lambda kv: -kv[1])
		],
		"rows": rows,
	}
