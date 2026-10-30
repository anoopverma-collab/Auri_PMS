"""Visibility rules (spec section 2): permission_query_conditions and has_permission hooks.

These hooks only decide *visibility* (can the user see the record at all). Capability errors such as
"You are not allowed to create work items" are raised by the controllers so that the messages stay
specific and testable.
"""

from __future__ import annotations

import frappe
from frappe.utils import cint

from auri_pms.auri_pms.utils import (
	can_create_doctype,
	can_manage_modules,
	get_capabilities,
	get_member_role,
	has_unrestricted_project_view,
	is_admin,
	is_allocated,
	is_user_enabled,
)


def _project_scope(user: str, column: str) -> str:
	"""Return an SQL condition limiting ``column`` (a project name column) to projects ``user`` can see.

	Returns an empty string when the user is unrestricted and ``1=0`` when the user is disabled.
	"""
	if is_admin(user):
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
	"""Return True if ``user`` may VIEW ``project``: an admin, a member, or anyone for a public project (editing needs allocation)."""
	user = user or frappe.session.user
	if is_admin(user):
		return True
	if not project or not is_user_enabled(user):
		return False
	if get_member_role(project, user):
		return True
	return bool(
		cint(frappe.db.get_value("Project", project, "is_public"))
	)  # public: viewable, never editable


# --------------------------------------------------------------------------- query conditions
def project_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Project."""
	user = user or frappe.session.user
	if has_unrestricted_project_view(user):
		return ""
	return _project_scope(user, "`tabProject`.name")


def work_item_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Work Item.

	A member whose Project Role has *Can See All Work Items* ticked sees every Work Item of the project. With it
	unticked the member sees only the Work Items assigned to them (Assigned To or Additional Assignees) or raised
	by them (Author). Admins, and a public project the user is not a member of, are unchanged."""
	user = user or frappe.session.user
	scope = _project_scope(user, "`tabWork Item`.project")
	if not scope or not is_user_enabled(user):
		return scope
	quoted = frappe.db.escape(user)
	limited = (
		"`tabWork Item`.project in (select pm.parent from `tabProject Member` pm "
		f"where pm.parenttype = 'Project' and pm.user = {quoted} and ifnull(pm.project_role, '') not in "
		"(select pr.name from `tabProject Role` pr where pr.can_see_all_items = 1))"
	)
	own = (
		f"(`tabWork Item`.assigned_to = {quoted} or `tabWork Item`.author = {quoted} or `tabWork Item`.name in "
		"(select wa.parent from `tabWork Item Assignee` wa "
		f"where wa.parenttype = 'Work Item' and wa.user = {quoted}))"
	)
	return f"({scope} and not ({limited} and not {own}))"


def sees_only_own_work_items(project: str | None, user: str) -> bool:
	"""True when ``user`` is a member of ``project`` whose Project Role may see only the Work Items assigned to them."""
	if not project or is_admin(user):
		return False
	if not get_member_role(project, user):
		return False
	return not get_capabilities(project, user, members_only=True)["can_see_all_items"]


def release_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Release."""
	return _project_scope(user or frappe.session.user, "`tabRelease`.project")


def risk_register_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Risk Register."""
	return _project_scope(user or frappe.session.user, "`tabRisk Register`.project")


def time_entry_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Time Entry."""
	return _project_scope(user or frappe.session.user, "`tabTime Entry`.project")


def sprint_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Sprint."""
	return _project_scope(user or frappe.session.user, "`tabSprint`.project")


def status_report_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Project Status Report."""
	return _project_scope(user or frappe.session.user, "`tabProject Status Report`.project")


def project_module_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Project Module: shared modules are listed only to those who may manage them."""
	user = user or frappe.session.user
	return "" if can_manage_modules(user) else "(1=0)"


def snapshot_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Project Dashboard Snapshot."""
	return _project_scope(user or frappe.session.user, "`tabProject Dashboard Snapshot`.project")


def category_query(user: str | None = None, doctype: str | None = None) -> str:
	"""permission_query_conditions for Work Item Category: only the categories of projects the user manages them in.

	Members still pick a category on a work item: that dropdown has its own query (``category_link_query``)."""
	user = user or frappe.session.user
	if is_admin(user):
		return ""
	if not is_user_enabled(user):
		return "(1=0)"
	return (
		"`tabWork Item Category`.project in (select pm.parent from `tabProject Member` pm "
		"join `tabProject Role` pr on pr.name = pm.project_role and pr.can_manage_categories = 1 "
		f"where pm.parenttype = 'Project' and pm.user = {frappe.db.escape(user)})"
	)


# --------------------------------------------------------------------------- has_permission
# Anything that changes a record: only the people allocated to its project (or an admin) may do it.
CHANGE_TYPES = frozenset({"write", "delete", "submit", "cancel", "amend"})


def _has_project_permission(doc, ptype: str | None, user: str | None, project_field: str = "project") -> bool:
	user = user or frappe.session.user
	if is_admin(user):
		return True
	if not is_user_enabled(user):
		return False
	# Creation is checked by the controllers (R-04, R-34, R-39 ...) so the user gets a specific message.
	if ptype == "create":
		return True
	project = doc.get(project_field)
	if not project:
		return True
	if ptype in CHANGE_TYPES and not is_allocated(project, user):
		return False
	return can_see_project(project, user)


def project_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Project."""
	user = user or frappe.session.user
	if is_admin(user):
		return True
	if not is_user_enabled(user):
		return False
	if ptype == "create" or doc.is_new():
		return True
	if (
		ptype in CHANGE_TYPES
		and cint(frappe.db.get_value("Project", doc.name, "pms_enabled"))
		and not is_allocated(doc.name, user)
	):
		return False  # an ERPNext Projects role does not let you edit a project you are not allocated to
	if has_unrestricted_project_view(user):
		return True
	return can_see_project(doc.name, user)


def work_item_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Work Item."""
	user = user or frappe.session.user
	if not _has_project_permission(doc, ptype, user):
		return False
	if ptype == "create" or doc.is_new() or not sees_only_own_work_items(doc.get("project"), user):
		return True
	return user in (doc.get("assigned_to"), doc.get("author")) or any(
		row.user == user for row in doc.get("additional_assignees") or []
	)


def release_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Release."""
	return _has_project_permission(doc, ptype, user)


def risk_register_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Risk Register."""
	return _has_project_permission(doc, ptype, user)


def time_entry_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Time Entry."""
	return _has_project_permission(doc, ptype, user)


def project_module_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Project Module: only those who may manage modules see or change them."""
	return can_manage_modules(user or frappe.session.user)


def snapshot_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Project Dashboard Snapshot."""
	return _has_project_permission(doc, ptype, user)


def category_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Work Item Category: only those who may manage categories on its project."""
	user = user or frappe.session.user
	if is_admin(user):
		return True
	if doc.is_new() and not doc.get("project"):
		return can_create_doctype("Work Item Category", user)  # the form is opened before a project is chosen
	return _has_project_permission(doc, ptype, user) and get_capabilities(doc.get("project"), user)[
		"can_manage_categories"
	]


def sprint_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Sprint."""
	return _has_project_permission(doc, ptype, user)


def status_report_has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	"""has_permission hook for Project Status Report."""
	return _has_project_permission(doc, ptype, user)
