"""doc_events and dashboard for the ERPNext Project extension (spec section 4, rule R-02)."""

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

from auri_pms.auri_pms.utils import (
	clear_cache,
	get_capabilities,
	has_unrestricted_project_view,
	is_manager,
)

IDENTIFIER_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")
TRACKER_ROLES = {"Tracker User", "Tracker Manager"}
PROJECT_RECORDS = ("Work Item", "Release", "Risk Register", "Sprint", "Time Entry")
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
	validate_tracker_permissions(doc, old)
	warn_about_removed_members(doc, old)
	set_default_ticket_types(doc, old)


def on_update(doc, method: str | None = None) -> None:
	"""Project.on_update hook: give members the Tracker User role and refresh caches."""
	clear_cache()
	added = []
	for row in doc.get("tracker_members") or []:
		if TRACKER_ROLES & set(frappe.get_roles(row.user)):
			continue
		user = frappe.get_doc("User", row.user)
		user.flags.ignore_permissions = True
		user.add_roles("Tracker User")
		added.append(row.user)
	if added:
		frappe.msgprint(
			_("The Tracker User role was added to: {0}").format(", ".join(added)),
			indicator="blue",
			alert=True,
		)


def on_trash(doc, method: str | None = None) -> None:
	"""Project.on_trash hook: refresh caches."""
	clear_cache()


def validate_enabled(doc, old) -> None:
	"""Enable Auri PMS needs an identifier and cannot be removed while the project has Auri PMS records."""
	if cint(doc.get("pms_enabled")) and not doc.get("tracker_identifier"):
		frappe.throw(_("Set an Identifier to enable Auri PMS on this project"))
	if old and cint(old.get("pms_enabled")) and not cint(doc.get("pms_enabled")):
		for doctype in PROJECT_RECORDS:
			if frappe.db.exists(doctype, {"project": doc.name}):
				frappe.throw(
					_("Auri PMS cannot be disabled on Project {0}: it still has {1} records").format(
						doc.name, _(doctype)
					)
				)


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


def _tracker_state(doc) -> tuple:
	"""Comparable snapshot of the fields only managers may change."""
	return (
		cint(doc.get("pms_enabled")),
		cint(doc.get("is_public")),
		sorted((r.user, r.project_role) for r in doc.get("tracker_members") or []),
		sorted(r.tracker for r in doc.get("enabled_trackers") or []),
	)


def validate_tracker_permissions(doc, old) -> None:
	"""Only a manager or a member with can_manage_members changes members, visibility or trackers."""
	empty = (0, 0, [], [])
	before = _tracker_state(old) if old else empty
	if _tracker_state(doc) != before and not is_manager():
		allowed = bool(old) and get_capabilities(doc.name)["can_manage_members"]
		if not allowed:
			frappe.throw(
				_("You are not allowed to change members, visibility or trackers of Project {0}").format(
					doc.name or doc.project_name
				)
			)
	if old and not has_unrestricted_project_view(frappe.session.user):
		# A pure Tracker User may only change the tracker fields of an ERPNext Project.
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


def warn_about_removed_members(doc, old) -> None:
	"""Removing a member who has open assigned items is allowed, but warn and list the items."""
	if not old:
		return
	removed = {r.user for r in old.get("tracker_members") or []} - {
		r.user for r in doc.get("tracker_members") or []
	}
	if not removed:
		return
	items = frappe.get_all(
		"Work Item",
		filters={"project": doc.name, "assigned_to": ["in", list(removed)], "is_closed": 0},
		pluck="name",
	)
	if items:
		frappe.msgprint(
			_("Removed members still have open assigned items: {0}").format(", ".join(items)),
			indicator="orange",
		)


def get_dashboard_data(data: dict) -> dict:
	"""override_doctype_dashboards hook: add Work Items, Releases and Time Entries to the Project dashboard."""
	data.setdefault("transactions", []).append(
		{"label": _("Auri PMS"), "items": ["Work Item", "Release", "Risk Register", "Time Entry"]}
	)
	return data
