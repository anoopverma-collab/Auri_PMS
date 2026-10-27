"""doc_events and dashboard for the ERPNext Project extension (spec section 4, rule R-02)."""

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.utils import cint, cstr, flt

from auri_pms.auri_pms.doctype.work_item.work_item import CUSTOM_FIELD_COUNT, close_todos, project_custom_values
from auri_pms.auri_pms.utils import (
	clear_cache,
	get_capabilities,
	has_unrestricted_project_view,
	is_admin,
	safe_sendmail,
)

IDENTIFIER_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")
TRACKER_ROLES = {"Auri PMS User", "Auri PMS Manager", "Auri PMS Admin"}
PROJECT_RECORDS = ("Work Item", "Release", "Risk Register", "Sprint", "Time Entry")
# Filters that select the still-open records; Time Entry has no open/closed state.
OPEN_FILTERS = {
	"Work Item": {"is_closed": 0},
	"Release": {"status": ("!=", "Closed")},
	"Risk Register": {"status": ("!=", "Closed")},
	"Sprint": {"status": ("!=", "Completed")},
}
LAYOUT_FIELDTYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Button", "Fold"}
TRACKER_FIELDS = {
	"pms_enabled",
	"tracker_identifier",
	"parent_project",
	"is_public",
	"tracker_members",
	"enabled_trackers",
}


def validate(doc, method: str | None = None) -> None:
	"""Project.validate hook: identifier, parent, members and who may change what."""
	old = doc.get_doc_before_save()
	validate_enabled(doc, old)
	validate_identifier(doc, old)
	validate_parent_project(doc)
	validate_members(doc, old)
	set_role_permissions(doc)
	validate_tracker_permissions(doc, old)
	set_default_ticket_types(doc, old)


def sync_custom_values(doc) -> None:
	"""Pass a changed project custom value on to the tickets that still hold the old one (a background job)."""
	fields = ["pms_custom_count", *(f"pms_custom_{n}" for n in range(1, CUSTOM_FIELD_COUNT + 1))]
	if doc.is_new() or not any(doc.has_value_changed(f) for f in fields):
		return
	before = doc.get_doc_before_save()
	old = {f: before.get(f) for f in fields} if before else {}
	frappe.enqueue(
		"auri_pms.auri_pms.project_hooks.apply_custom_values",
		project=doc.name,
		old=old,
		queue="long",
		enqueue_after_commit=True,
		now=frappe.in_test,
	)


def apply_custom_values(project: str, old: dict) -> None:
	"""Save each ticket of ``project`` with the new custom values, so validation and the version history apply.

	A ticket follows the project when it holds the old project value (or none); a value typed on the ticket is kept,
	and fields beyond the project's *Number of Custom Fields* are cleared."""
	values = project_custom_values(project)
	count = values["project_custom_count"]
	for name in frappe.get_all("Work Item", {"project": project}, pluck="name"):
		try:
			item = frappe.get_doc("Work Item", name)
			columns = ["project_custom_count", *(f"project_custom_{n}" for n in range(1, CUSTOM_FIELD_COUNT + 1))]
			current = [item.get(c) for c in columns]
			item.project_custom_count = count
			for n in range(1, CUSTOM_FIELD_COUNT + 1):
				column, new = f"project_custom_{n}", values[f"project_custom_{n}"]
				if n > count:
					item.set(column, None)
				elif not item.get(column) or item.get(column) == (old.get(f"pms_custom_{n}") or None):
					item.set(column, new)
			if [item.get(c) for c in columns] == current:
				continue
			item.flags.ignore_permissions = True
			item.flags.ignore_tracker_rules = True
			item.save()
		except Exception:
			frappe.log_error(title=f"Auri PMS: custom values not copied to {name}")


def on_update(doc, method: str | None = None) -> None:
	"""Project.on_update hook: give members the Auri PMS User role, release removed members' items, refresh caches."""
	clear_cache()
	release_removed_members(doc)
	sync_custom_values(doc)
	added = []
	for row in doc.get("tracker_members") or []:
		if TRACKER_ROLES & set(frappe.get_roles(row.user)):
			continue
		user = frappe.get_doc("User", row.user)
		user.flags.ignore_permissions = True
		user.add_roles("Auri PMS User")
		added.append(row.user)
	if added:
		frappe.msgprint(
			_("The Auri PMS User role was added to: {0}").format(", ".join(added)),
			indicator="blue",
			alert=True,
		)


def on_trash(doc, method: str | None = None) -> None:
	"""Project.on_trash hook: refresh caches."""
	clear_cache()


def validate_enabled(doc, old) -> None:
	"""Enable Auri PMS needs an identifier; switching it off with Auri PMS records needs a confirmation."""
	if cint(doc.get("pms_enabled")) and not doc.get("tracker_identifier"):
		frappe.throw(_("Set an Identifier to enable Auri PMS on this project"))
	if old and cint(old.get("pms_enabled")) and not cint(doc.get("pms_enabled")):
		if any(row["total"] for row in get_record_counts(doc.name)) and not _consume_disable_confirmation(
			doc.name
		):
			frappe.throw(
				_(
					"Auri PMS cannot be disabled on Project {0} until you confirm: it still has records"
				).format(doc.name)
			)


def _confirmation_key(project: str) -> str:
	return f"auri_pms_disable_confirmed:{frappe.session.user}:{project}"


def _consume_disable_confirmation(project: str) -> bool:
	"""True once per confirmation: the token set by confirm_disable is removed when it is used."""
	key = _confirmation_key(project)
	confirmed = bool(frappe.cache.get_value(key))
	frappe.cache.delete_value(key)
	return confirmed


@frappe.whitelist()
def get_record_counts(project: str) -> list[dict]:
	"""Total and open count of every Auri PMS doctype on ``project``; ``open`` is None without a status."""
	frappe.has_permission("Project", "read", project, throw=True)
	counts = []
	for doctype in PROJECT_RECORDS:
		open_filters = OPEN_FILTERS.get(doctype)
		counts.append(
			{
				"doctype": doctype,
				"label": _(doctype),
				"total": frappe.db.count(doctype, {"project": project}),
				"open": frappe.db.count(doctype, {"project": project, **open_filters})
				if open_filters
				else None,
			}
		)
	return counts


@frappe.whitelist()
def confirm_disable(project: str) -> None:
	"""The user said yes to disabling Auri PMS: allow the next save of this project to do it (5 minutes)."""
	frappe.has_permission("Project", "write", project, throw=True)
	frappe.cache.set_value(_confirmation_key(project), 1, expires_in_sec=300)


def set_default_ticket_types(doc, old) -> None:
	"""When Auri PMS is switched on, enable every active Ticket Type unless some were already chosen."""
	if not cint(doc.get("pms_enabled")) or (old and cint(old.get("pms_enabled"))):
		return
	if doc.get("enabled_trackers"):
		return
	for name in frappe.get_all("Ticket Type", filters={"is_active": 1}, pluck="name", order_by="name"):
		doc.append("enabled_trackers", {"tracker": name})


def validate_identifier(doc, old) -> None:
	"""R-02: 2-10 chars, uppercase letters/digits, starts with a letter, unique, set once."""
	value = doc.get("tracker_identifier")
	old_value = old.get("tracker_identifier") if old else None
	if old_value and value != old_value:
		frappe.throw(_("Value cannot be changed for {0}").format(frappe.bold(_("Identifier"))))
	if not value:
		return
	if not IDENTIFIER_PATTERN.match(value):
		frappe.throw(_("Identifier must be 2-10 uppercase letters or digits and start with a letter"))
	other = frappe.db.get_value(
		"Project", {"tracker_identifier": value, "name": ("!=", doc.name or "")}, "name"
	)
	if other:
		frappe.throw(_("Identifier {0} is already used by Project {1}").format(value, other))


def validate_parent_project(doc) -> None:
	"""Parent Project: not self and no cycles."""
	parent = doc.get("parent_project")
	if not parent:
		return
	if parent == doc.name:
		frappe.throw(_("Parent Project cannot be the project itself"))
	seen = {parent}
	while parent:
		parent = frappe.db.get_value("Project", parent, "parent_project")
		if parent == doc.name:
			frappe.throw(_("Parent Project would create a cycle"))
		if not parent or parent in seen:
			break
		seen.add(parent)


def validate_members(doc, old) -> None:
	"""Unique enabled users, and at least one member with a Manager-type role."""
	members = doc.get("tracker_members") or []
	old_users = {r.user for r in (old.get("tracker_members") or [])} if old else set()
	seen: set[str] = set()
	for row in members:
		if row.user in seen:
			frappe.throw(_("{0} is added more than once in Members").format(row.user))
		seen.add(row.user)
		if row.user not in old_users and not cint(frappe.db.get_value("User", row.user, "enabled")):
			frappe.throw(_("User {0} is disabled and cannot be added as a member").format(row.user))
	if members and not any(
		cint(frappe.db.get_value("Project Role", r.project_role, "can_manage_members")) for r in members
	):
		frappe.throw(_("A project must keep at least one member with a Manager role"))


@frappe.whitelist()
def get_role_permissions(project_role: str) -> str:
	"""Comma separated list of what a Project Role allows, e.g. "Create Items, Log Time"."""
	role = frappe.get_cached_doc("Project Role", project_role)
	return ", ".join(
		_(df.label).removeprefix("Can ")
		for df in role.meta.fields
		if df.fieldtype == "Check" and cint(role.get(df.fieldname))
	)


def set_role_permissions(doc) -> None:
	"""Keep the Role Permissions column of the members table in step with the Project Roles."""
	for row in doc.get("tracker_members") or []:
		row.role_permissions = get_role_permissions(row.project_role) if row.project_role else ""


def _tracker_state(doc) -> tuple:
	"""Comparable snapshot of the fields only managers may change (pms_enabled has its own permission level)."""
	return (
		cint(doc.get("is_public")),
		sorted((r.user, r.project_role) for r in doc.get("tracker_members") or []),
		sorted(r.tracker for r in doc.get("enabled_trackers") or []),
	)


def validate_tracker_permissions(doc, old) -> None:
	"""Only a manager or a member with can_manage_members changes members, visibility or trackers."""
	empty = (0, [], [])
	before = _tracker_state(old) if old else empty
	if _tracker_state(doc) != before and not is_admin():
		allowed = bool(old) and get_capabilities(doc.name)["can_manage_members"]
		if not allowed:
			frappe.throw(
				_("You are not allowed to change members, visibility or trackers of Project {0}").format(
					doc.name or doc.project_name
				)
			)
	if old and not has_unrestricted_project_view(frappe.session.user):
		# A pure Auri PMS User may only change the tracker fields of an ERPNext Project.
		for df in doc.meta.fields:
			if df.read_only or df.fieldtype in LAYOUT_FIELDTYPES or df.fieldname in TRACKER_FIELDS:
				continue
			if df.fieldtype in frappe.model.table_fields:
				continue
			if not _same_value(df, doc.get(df.fieldname), old.get(df.fieldname)):
				frappe.throw(_("You can only change the Auri PMS tab of Project {0}").format(doc.name))


def _same_value(df, new, old) -> bool:
	"""Compare two field values, tolerating 0 vs 0.0 and None vs empty."""
	if df.fieldtype in frappe.model.numeric_fieldtypes:
		return flt(new) == flt(old)
	return cstr(new) == cstr(old)


def release_removed_members(doc) -> None:
	"""Removing a member unassigns their open work items and tells them and the project managers."""
	old = doc.get_doc_before_save()
	if not old:
		return
	removed = {r.user for r in old.get("tracker_members") or []} - {
		r.user for r in doc.get("tracker_members") or []
	}
	if not removed:
		return
	released: dict[str, list[str]] = {}
	for item in frappe.get_all(
		"Work Item",
		filters={"project": doc.name, "assigned_to": ["in", list(removed)], "is_closed": 0},
		fields=["name", "assigned_to"],
		order_by="name",
	):
		_unassign(item.name, item.assigned_to, doc.name)
		released.setdefault(item.assigned_to, []).append(item.name)
	for user in removed:
		_tell_removed_member(user, doc.name, released.get(user, []))
	if released:
		_tell_managers(doc, released)
		frappe.msgprint(
			_("{0} open items of the removed members were unassigned: {1}").format(
				sum(len(items) for items in released.values()),
				", ".join(name for items in released.values() for name in items),
			),
			indicator="orange",
		)


def _unassign(work_item: str, user: str, project: str) -> None:
	"""Clear the assignee without the Work Item rules (the member is already gone) and close their ToDo."""
	frappe.db.set_value("Work Item", work_item, "assigned_to", None)
	close_todos(work_item, user)
	frappe.get_doc("Work Item", work_item).add_comment(
		"Info", _("Unassigned from {0}: removed from Project {1}").format(user, project)
	)


def _tell_removed_member(user: str, project: str, items: list[str]) -> None:
	"""In-app notification and email to the removed member; the list is empty when nothing was assigned."""
	if items:
		subject = _(
			"You were removed from Project {0}. These open items were unassigned from you: {1}"
		).format(frappe.bold(project), ", ".join(items))
	else:
		subject = _("You were removed from Project {0}").format(frappe.bold(project))
	if frappe.db.get_value("User", user, "enabled"):
		enqueue_create_notification(
			[user],
			{"type": "Alert", "subject": subject, "from_user": frappe.session.user},
		)
		safe_sendmail(
			recipients=[user],
			subject=_("Removed from Project {0}").format(project),
			message=subject,
		)


def _tell_managers(doc, released: dict[str, list[str]]) -> None:
	"""In-app notification to the members who manage members, except the user who made the change."""
	managers = {
		r.user
		for r in doc.get("tracker_members") or []
		if cint(frappe.db.get_value("Project Role", r.project_role, "can_manage_members"))
	} - {frappe.session.user}
	if not managers:
		return
	lines = "; ".join(f"{user}: {', '.join(items)}" for user, items in released.items())
	enqueue_create_notification(
		list(managers),
		{
			"type": "Alert",
			"document_type": "Project",
			"document_name": doc.name,
			"subject": _(
				"Members were removed from Project {0}; their open items were unassigned. {1}"
			).format(frappe.bold(doc.name), lines),
			"from_user": frappe.session.user,
		},
	)


def get_dashboard_data(data: dict) -> dict:
	"""override_doctype_dashboards hook: add Work Items, Releases and Time Entries to the Project dashboard."""
	data.setdefault("transactions", []).append(
		{"label": _("Auri PMS"), "items": ["Work Item", "Release", "Risk Register", "Time Entry"]}
	)
	return data
