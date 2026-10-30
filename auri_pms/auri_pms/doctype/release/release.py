"""Release - plans work items and rolls up their progress (spec 3.7, R-33 .. R-36, N-5)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.model.document import Document

from auri_pms.auri_pms.utils import ensure_pms_project, has_capability, linked_tickets


class Release(Document):
	"""A planned delivery of work items within one project."""

	def before_insert(self) -> None:
		"""The project identifier is part of the name, so fetch it before naming."""
		self.set_project_identifier()

	def validate(self) -> None:
		"""R-34 capability and R-35 closing rule."""
		self.set_project_identifier()
		self.validate_can_manage()
		self.validate_can_close()

	def set_project_identifier(self) -> None:
		"""Copy the project identifier (needed for the document name)."""
		ensure_pms_project(self.project, _("creating releases"))
		identifier = frappe.db.get_value("Project", self.project, "tracker_identifier")
		if not identifier:
			frappe.throw(_("Set an Identifier on Project {0} before creating releases").format(self.project))
		self.project_identifier = identifier

	def validate_can_manage(self) -> None:
		"""R-34: only users with can_manage_releases (or managers) create or edit releases."""
		if not has_capability(self.project, "can_manage_releases"):
			frappe.throw(_("You are not allowed to manage releases in Project {0}").format(self.project))

	def validate_can_close(self) -> None:
		"""R-35: a release cannot be Closed while it has open items."""
		if self.status != "Closed":
			return
		previous = self.get_doc_before_save()
		if previous and previous.status == "Closed":
			return
		open_items = frappe.db.count("Work Item", {"release": self.name, "is_closed": 0})
		if open_items:
			frappe.throw(_("Move or close {0} open items before closing this release").format(open_items))

	def on_update(self) -> None:
		"""N-5: tell all project members when a release is moved to Closed."""
		previous = self.get_doc_before_save()
		if self.status != "Closed" or (previous and previous.status == "Closed"):
			return
		members = frappe.get_all(
			"Project Member", filters={"parent": self.project, "parenttype": "Project"}, pluck="user"
		)
		if members:
			enqueue_create_notification(
				members,
				{
					"type": "Alert",
					"document_type": "Release",
					"document_name": self.name,
					"subject": _("Release {0} of Project {1} was closed").format(
						frappe.bold(self.name), frappe.bold(self.project)
					),
					"from_user": frappe.session.user,
				},
			)

	def on_trash(self) -> None:
		"""R-34 applies to deletion; R-36 (items linked) is enforced by Frappe's link check."""
		self.validate_can_manage()


@frappe.whitelist()
def get_release_tickets(release: str) -> dict:
	"""The tickets allocated to a release: a count per status and per person, plus the tickets themselves."""
	frappe.has_permission("Release", "read", doc=release, throw=True)
	return linked_tickets("release", release)
