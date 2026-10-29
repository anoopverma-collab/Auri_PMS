"""Install and uninstall hooks plus idempotent default data (spec section 7)."""

from __future__ import annotations

import frappe
from frappe import _

from auri_pms.auri_pms.utils import nearest_indicator

BOARD_NAME = "Work Items by Status"

# name, sequence, is_closed, default_done_percent, colour (hex), kanban indicator
STATUSES = [
	("New", 10, 0, 0, "#2490EF", "Blue"),
	("In Progress", 20, 0, None, "#FF9F1C", "Orange"),
	("Feedback", 30, 0, None, "#FACC15", "Yellow"),
	("Resolved", 40, 0, 90, "#8B5CF6", "Purple"),
	("Closed", 50, 1, 100, "#22C55E", "Green"),
	("Rejected", 60, 1, None, "#8D99A6", "Gray"),
]
INDICATORS = {s[0]: s[5] for s in STATUSES}

_FLAGS_ALL = (
	"can_create_items can_edit_any_item can_delete_items can_manage_releases can_manage_categories "
	"can_log_time can_edit_others_time can_manage_members can_be_assigned"
).split()
PROJECT_ROLES = {
	"Manager": _FLAGS_ALL,
	"Developer": ["can_create_items", "can_edit_any_item", "can_log_time", "can_be_assigned"],
	"Reporter": ["can_create_items", "can_log_time"],
	"Functional": [
		"can_create_items",
		"can_edit_any_item",
		"can_manage_categories",
		"can_log_time",
		"can_be_assigned",
	],
}

BUG_WORKFLOW = [
	("New", "In Progress", None),
	("New", "Rejected", "Manager"),
	("In Progress", "Feedback", None),
	("Feedback", "In Progress", None),
	("In Progress", "Resolved", "Developer"),
	("In Progress", "Resolved", "Manager"),
	("Resolved", "Closed", "Reporter"),
	("Resolved", "Closed", "Manager"),
	("Resolved", "In Progress", None),
	("Closed", "In Progress", "Manager"),
	("Rejected", "New", "Manager"),
]
TRACKERS = {"Bug": "#E24C4C", "Feature": "#2490EF", "Task": "#22C55E", "Support": "#8B5CF6"}
ACTIVITY_TYPES = ["Development", "Design", "Testing", "Meeting", "Support", "Documentation"]


# The roles of the app, from the widest to the narrowest. Auri PMS Admin and System Manager see and do everything in every
# project; Auri PMS Manager and Auri PMS User only work in the projects they are a member of, with the rights of their Project Role.
ROLES = ("Auri PMS Admin", "Auri PMS Manager", "Auri PMS User")


def ensure_roles() -> None:
	"""Create the app's roles when they are missing (idempotent; the fixtures hold the same list for export)."""
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1, "is_custom": 1}).insert(
				ignore_permissions=True
			)


def after_install() -> None:
	"""Create the roles and default data once (idempotent) and prepare the Project permissions and Kanban board."""
	ensure_roles()
	create_default_data()
	ensure_email_templates()
	ensure_kanban_board()
	ensure_project_permissions()
	ensure_workspace_docs()


def ensure_workspace_docs() -> None:
	"""Make the sidebar and the app icon match the files in this app on every install and migrate.

	The files are the source of truth, so a site that holds an older or edited copy gets the same workspace as every
	other site (a plain Frappe sync only replaces a copy when the file's modified time is newer).
	"""
	from frappe.modules.import_file import import_file_by_path

	for folder in ("workspace_sidebar", "desktop_icon"):
		import_file_by_path(
			frappe.get_app_path("auri_pms", folder, "auri_pms.json"), force=True, ignore_version=True
		)
	# Frappe 16.52 and later read a module's sidebar from a Sidebar document (the old Workspace Sidebar is an archive
	# there and is no longer read); older versions have no such doctype and use the file above.
	if frappe.db.exists("DocType", "Sidebar"):
		import_file_by_path(
			frappe.get_app_path("auri_pms", "auri_pms", "sidebar", "auri_pms", "auri_pms.json"),
			force=True,
			ignore_version=True,
		)


def after_migrate() -> None:
	"""Keep the roles, Project permissions, the sidebar and the app icon in line with the code after migrate; master data is never touched."""
	ensure_roles()
	ensure_project_permissions()
	ensure_workspace_docs()
	ensure_email_templates()
	enable_shipped_email_templates()


def create_default_data() -> None:
	"""Create statuses, project roles, trackers, activity types and settings; skip anything that exists."""
	for name, sequence, is_closed, done, colour, _indicator in STATUSES:
		insert_if_missing(
			"Work Item Status",
			name,
			{
				"status_name": name,
				"sequence": sequence,
				"is_closed": is_closed,
				"default_done_percent": done,
				"color": colour,
				"is_active": 1,
			},
		)
	for role, flags in PROJECT_ROLES.items():
		insert_if_missing("Project Role", role, {"role_name": role, **dict.fromkeys(flags, 1)})
	for tracker, colour in TRACKERS.items():
		values = {
			"tracker_name": tracker,
			"color": colour,
			"default_status": "New",
			"is_active": 1,
			"is_defect": int(tracker == "Bug"),
		}
		if tracker == "Bug":
			values["transitions"] = [
				{"from_status": f, "to_status": t, "project_role": r} for f, t, r in BUG_WORKFLOW
			]
		insert_if_missing("Ticket Type", tracker, values)
	for activity in ACTIVITY_TYPES:
		insert_if_missing("Activity Type", activity, {"activity_type": activity})
	settings = frappe.get_doc("PMS Settings")
	if not settings.default_status:
		settings.update(
			{"default_status": "New", "default_priority": "Normal", "public_project_role": "Reporter"}
		)
		settings.flags.ignore_permissions = True
		settings.save()


# Email Template name, subject and file in templates/emails (pick one in PMS Settings > Status Report)
_REPORT_SUBJECT = (
	"{{ r.project.project_name }}: status report "
	"{{ frappe.utils.formatdate(r.from_date) }} to {{ frappe.utils.formatdate(r.to_date) }}"
)
EMAIL_TEMPLATES = [
	("PMS Status Report - Summary", _REPORT_SUBJECT, "pms_status_report_summary.html"),
	("PMS Status Report - Corporate", _REPORT_SUBJECT, "pms_status_report_detailed.html"),
	("PMS Status Report - Summary Dark", _REPORT_SUBJECT, "pms_status_report_summary_dark.html"),
	("PMS Status Report - Corporate Grey", _REPORT_SUBJECT, "pms_status_report_detailed_grey.html"),
]


def template_html(filename: str) -> str:
	"""The HTML of a ready-made template; ``filename`` is one of the constants in EMAIL_TEMPLATES."""
	path = frappe.get_app_path("auri_pms", "templates", "emails", filename)
	# a file shipped with the app; no user input is part of the path
	# nosemgrep: frappe-security-file-traversal
	with open(path, encoding="utf-8") as f:
		return f.read()


def ensure_template_flag() -> None:
	"""Make sure Email Template has its *Enable for Auri PMS* checkbox.

	On a fresh install Frappe runs after_install before it syncs the app's fixtures, so the field is created here
	first; the fixture later finds it already in place."""
	name = "Email Template-auri_pms_enabled"
	if frappe.db.exists("Custom Field", name):
		return
	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "Email Template",
			"fieldname": "auri_pms_enabled",
			"fieldtype": "Check",
			"label": "Enable for Auri PMS",
			"default": "0",
			"description": "Offer this template for the client status report in Auri PMS",
			"in_standard_filter": 1,
			"insert_after": "subject",
			"module": "Auri PMS",
		}
	).insert(ignore_permissions=True)


def ensure_email_templates(overwrite: bool = False) -> None:
	"""Create the ready-made status report Email Templates; an existing (possibly edited) one is kept unless ``overwrite``."""
	ensure_template_flag()
	for name, subject, filename in EMAIL_TEMPLATES:
		values = {
			"name": name,
			"subject": subject,
			"use_html": 1,
			"response_html": template_html(filename),
			"auri_pms_enabled": 1,
		}
		if not insert_if_missing("Email Template", name, values) and overwrite:
			frappe.db.set_value("Email Template", name, {k: v for k, v in values.items() if k != "name"})


def enable_shipped_email_templates() -> None:
	"""Tick "Enable for Auri PMS" on the ready-made templates once; a template switched off later stays off."""
	marker = "auri_pms_templates_enabled"
	if frappe.db.get_default(marker) or not frappe.db.has_column("Email Template", "auri_pms_enabled"):
		return
	for name, *_rest in EMAIL_TEMPLATES:
		if frappe.db.exists("Email Template", name):
			frappe.db.set_value("Email Template", name, "auri_pms_enabled", 1)
	frappe.db.set_default(marker, "1")


def insert_if_missing(doctype: str, name: str, values: dict) -> bool:
	"""Insert ``doctype`` ``name`` with ``values`` unless it exists. Returns True when created."""
	if frappe.db.exists(doctype, name):
		return False
	doc = frappe.get_doc({"doctype": doctype, **values})
	doc.flags.ignore_permissions = True
	doc.insert()
	return True


# --------------------------------------------------------------------------- Kanban
def ensure_kanban_board() -> None:
	"""Create the "Work Items by Status" Kanban board with one column per active status."""
	if not frappe.db.exists("Kanban Board", BOARD_NAME):
		board = frappe.get_doc(
			{
				"doctype": "Kanban Board",
				"kanban_board_name": BOARD_NAME,
				"reference_doctype": "Work Item",
				"field_name": "status",
				"private": 0,
				"show_labels": 0,
			}
		)
		board.flags.ignore_permissions = True
		board.insert()
	sync_board_columns()


def sync_board_columns() -> None:
	"""Make sure every active status has a column, ordered by sequence."""
	if not frappe.db.exists("Kanban Board", BOARD_NAME):
		return
	board = frappe.get_doc("Kanban Board", BOARD_NAME)
	existing = {c.column_name for c in board.columns}
	statuses = frappe.get_all(
		"Work Item Status",
		filters={"is_active": 1},
		fields=["name", "sequence", "color"],
		order_by="sequence asc",
	)
	missing = [s for s in statuses if s.name not in existing]
	if not missing:
		return
	for status in missing:
		board.append(
			"columns",
			{
				"column_name": status.name,
				"status": "Active",
				"indicator": INDICATORS.get(status.name, "Gray"),
			},
		)
	order = {s.name: s.sequence for s in statuses}
	board.columns.sort(key=lambda c: order.get(c.column_name, 10**6))
	for idx, column in enumerate(board.columns, start=1):
		column.idx = idx
	board.flags.ignore_permissions = True
	board.save()


def indicator_for(status_name: str, color: str | None = None) -> str:
	"""Kanban indicator for a status: the shipped default, else the nearest to its colour."""
	return INDICATORS.get(status_name) or nearest_indicator(color).capitalize()


def add_status_column(status: str) -> None:
	"""Called when a Work Item Status is inserted: add its Kanban column."""
	sync_board_columns()


# --------------------------------------------------------------------------- ERPNext permissions
# ERPNext DocTypes the tracker roles need, granted as Custom DocPerm (no core files are touched).
ERPNEXT_PERMISSIONS = {
	"Project": {
		"Auri PMS Admin": ("read", "write", "create", "report"),
		"Auri PMS Manager": ("read", "write", "create", "report"),
		"System Manager": ("read", "write", "create", "report"),  # inherits Auri PMS Manager rights
		"Auri PMS User": ("read", "write"),
	},
	"Activity Type": {  # needed to pick an activity when logging time
		"Auri PMS Admin": ("read",),
		"Auri PMS Manager": ("read",),
		"Auri PMS User": ("read",),
	},
}


# Enable Auri PMS sits on its own permission level: only these roles may switch a project on or off.
PMS_SWITCH_PERMLEVEL = 2
PMS_SWITCH_PERMISSIONS = {
	"System Manager": ("read", "write"),
	"Auri PMS Admin": ("read", "write"),
	"Auri PMS Manager": ("read", "write"),
	"Projects Manager": ("read", "write"),
	"Auri PMS User": ("read",),
	"Projects User": ("read",),
}


def ensure_project_permissions() -> None:
	"""Give the tracker roles access to the ERPNext DocTypes they work with (idempotent)."""
	from frappe.permissions import add_permission, update_permission_property

	for doctype, grants in ERPNEXT_PERMISSIONS.items():
		for role, ptypes in grants.items():
			if not frappe.db.exists("Role", role):
				continue
			add_permission(doctype, role, 0)
			for ptype in ptypes:
				update_permission_property(doctype, role, 0, ptype, 1)
	for role, ptypes in PMS_SWITCH_PERMISSIONS.items():
		if not frappe.db.exists("Role", role):
			continue
		add_permission("Project", role, PMS_SWITCH_PERMLEVEL)
		for ptype in ptypes:
			update_permission_property("Project", role, PMS_SWITCH_PERMLEVEL, ptype, 1)


# --------------------------------------------------------------------------- uninstall
def before_uninstall() -> None:
	"""Remove what the app added to other doctypes; ERPNext Activity Types stay untouched."""
	for name in frappe.get_all("Custom Field", filters={"module": "Auri PMS"}, pluck="name"):
		frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
	for doctype, grants in ERPNEXT_PERMISSIONS.items():
		for role in grants:
			if role == "System Manager" and doctype != "Project":
				continue  # ERPNext already grants System Manager on the other doctypes; that row is not ours
			for name in frappe.get_all(
				"Custom DocPerm", filters={"parent": doctype, "role": role}, pluck="name"
			):
				frappe.delete_doc("Custom DocPerm", name, force=True, ignore_permissions=True)
	for name in frappe.get_all(
		"Custom DocPerm", filters={"parent": "Project", "permlevel": PMS_SWITCH_PERMLEVEL}, pluck="name"
	):
		frappe.delete_doc("Custom DocPerm", name, force=True, ignore_permissions=True)
	if frappe.db.exists("Kanban Board", BOARD_NAME):
		frappe.delete_doc("Kanban Board", BOARD_NAME, force=True, ignore_permissions=True)
	# Database rows only: delete_doc would also delete the standard JSON files from the app in developer mode.
	for doctype, name in (
		("Workspace", "Tracker"),
		("Workspace Sidebar", "Tracker"),
		("Workspace Sidebar", "Auri PMS"),
		("Sidebar", "Auri PMS"),
		("Desktop Icon", "Tracker"),
		("Desktop Icon", "Auri PMS"),
		("Desktop Icon", "Auriga Track"),
	):
		if not frappe.db.exists("DocType", doctype):  # a Frappe version without that doctype
			continue
		frappe.db.delete(doctype, {"name": name})
		if doctype == "Sidebar":
			frappe.db.delete("Sidebar Item", {"parent": name})
	frappe.clear_cache()
