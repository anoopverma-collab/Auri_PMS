"""Visibility rules (spec section 2): permission_query_conditions and has_permission hooks.

These hooks only decide *visibility* (can the user see the record at all). Capability errors such as
"You are not allowed to create work items" are raised by the controllers so that the messages stay
specific and testable.
"""

from __future__ import annotations

import frappe
from frappe.utils import cint

from auriga_track.tracking.utils import (
	get_member_role,
	has_unrestricted_project_view,
	is_manager,
	is_user_enabled,
)


def _project_scope(user: str, column: str) -> str:
	"""Return an SQL condition limiting ``column`` (a project name column) to projects ``user`` can see.

	Returns an empty string when the user is unrestricted and ``1=0`` when the user is disabled.
	"""
	if is_manager(user):
		return ""
	if not is_user_enabled(user):
		return "(1=0)"
	quoted = frappe.db.escape(user)
	return (
		f"({column} in (select pm.parent from `tabProject Member` pm "
		f"where pm.parenttype = 'Project' and pm.user = {quoted}) "
		f"or {column} in (select p.name from `tabProject` p where p.is_public = 1))"
	)


def can_see_project(project: str | None, user: str | None = None) -> bool:
	"""Return True if ``user`` is a manager, a member of ``project`` or the project is public."""
	user = user or frappe.session.user
	if is_manager(user):
		return True
	if not project or not is_user_enabled(user):
		return False
	if get_member_role(project, user):
		return True
	return bool(cint(frappe.db.get_value("Project", project, "is_public")))


# --------------------------------------------------------------------------- query conditions
def project_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Project."""
	user = user or frappe.session.user
	if has_unrestricted_project_view(user):
		return ""
	return _project_scope(user, "`tabProject`.name")


def work_item_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Work Item."""
	return _project_scope(user or frappe.session.user, "`tabWork Item`.project")


def release_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Release."""
	return _project_scope(user or frappe.session.user, "`tabRelease`.project")


def time_entry_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Time Entry."""
	return _project_scope(user or frappe.session.user, "`tabTime Entry`.project")


def sprint_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Sprint."""
	return _project_scope(user or frappe.session.user, "`tabSprint`.project")


def category_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Work Item Category."""
	return _project_scope(user or frappe.session.user, "`tabWork Item Category`.project")


# --------------------------------------------------------------------------- has_permission
def _has_project_permission(doc, ptype: str | None, user: str | None, project_field: str = "project") -> bool:
	user = user or frappe.session.user
	if is_manager(user):
		return True
	if not is_user_enabled(user):
		return False
	# Creation is checked by the controllers (R-04, R-34, R-39 ...) so the user gets a specific message.
	if ptype == "create":
		return True
	project = doc.get(project_field)
	if not project:
		return True
	return can_see_project(project, user)


def project_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Project."""
	user = user or frappe.session.user
	if has_unrestricted_project_view(user):
		return True
	if not is_user_enabled(user):
		return False
	if ptype == "create" or doc.is_new():
		return True
	return can_see_project(doc.name, user)


def work_item_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Work Item."""
	return _has_project_permission(doc, ptype, user)


def release_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Release."""
	return _has_project_permission(doc, ptype, user)


def time_entry_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Time Entry."""
	return _has_project_permission(doc, ptype, user)


def category_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Work Item Category."""
	return _has_project_permission(doc, ptype, user)


def sprint_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Sprint."""
	return _has_project_permission(doc, ptype, user)
