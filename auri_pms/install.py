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
	"Reporter": ["can_create_items"],
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


def after_install() -> None:
	"""Create default data once (idempotent) and prepare the Project permissions and Kanban board."""
	create_default_data()
	ensure_kanban_board()
	ensure_project_permissions()
	ensure_workspace_docs()


def ensure_workspace_docs() -> None:
	"""Make sure the sidebar and the app icon exist right after install (a missing one is imported, never overwritten)."""
	from frappe.modules.import_file import import_file_by_path

	for folder, doctype in (("workspace_sidebar", "Workspace Sidebar"), ("desktop_icon", "Desktop Icon")):
		path = frappe.get_app_path("auri_pms", folder, "auri_pms.json")
		if not frappe.db.exists(doctype, "Auri PMS"):
			import_file_by_path(path, force=True, ignore_version=True)


def after_migrate() -> None:
	"""Keep Project permissions, the sidebar and the app icon in place after migrate; master data is never touched."""
	ensure_project_permissions()
	ensure_workspace_docs()


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
		"Tracker Manager": ("read", "write", "create", "report"),
		"System Manager": ("read", "write", "create", "report"),  # inherits Tracker Manager rights
		"Tracker User": ("read", "write"),
	},
	"Activity Type": {  # needed to pick an activity when logging time
		"Tracker Manager": ("read",),
		"Tracker User": ("read",),
	},
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
	if frappe.db.exists("Kanban Board", BOARD_NAME):
		frappe.delete_doc("Kanban Board", BOARD_NAME, force=True, ignore_permissions=True)
	# Database rows only: delete_doc would also delete the standard JSON files from the app in developer mode.
	for doctype, name in (
		("Workspace", "Tracker"),
		("Workspace Sidebar", "Tracker"),
		("Workspace Sidebar", "Auri PMS"),
		("Desktop Icon", "Tracker"),
		("Desktop Icon", "Auri PMS"),
		("Desktop Icon", "Auriga Track"),
	):
		frappe.db.delete(doctype, {"name": name})
	frappe.clear_cache()
