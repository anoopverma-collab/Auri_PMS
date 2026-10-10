"""Work Item - the core document of Auri PMS (spec 3.8, rules R-01 to R-33, R-37)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.form import assign_to
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint, flt, now_datetime, today

from auriga_track.tracking.utils import (
	compute_progress,
	follow_work_item,
	get_ancestors,
	get_capabilities,
	get_children,
	get_descendants,
	get_enabled_trackers,
	get_settings,
	get_subtree_height,
	recalc_chain,
	recalc_release,
	recalc_sprint,
	safe_sendmail,
	transition_allowed,
)

REVERSE_RELATION = {
	"Relates to": "Relates to",
	"Duplicates": "Duplicated by",
	"Duplicated by": "Duplicates",
	"Blocks": "Blocked by",
	"Blocked by": "Blocks",
	"Precedes": "Follows",
	"Follows": "Precedes",
}
TODO_PRIORITY = {"Low": "Low", "Normal": "Medium", "High": "High", "Urgent": "High", "Immediate": "High"}
ROLLUP_FIELDS = ("spent_hours", "total_spent_hours", "total_estimated_hours", "done_percent")


class WorkItem(Document):
	"""A bug, feature, task or support request tracked against a Project."""

	def onload(self) -> None:
		"""Tell the form whether this item has subtasks (its % Done is then read-only, R-31)."""
		self.set_onload("has_children", bool(get_children(self.name)))

	# ------------------------------------------------------------------ naming and creation (R-01, R-03, R-04)
	def before_insert(self) -> None:
		"""Reject creation before a series number is consumed (R-03, R-04)."""
		if not self.project:
			return
		identifier = frappe.db.get_value("Project", self.project, "tracker_identifier")
		if not identifier:
			frappe.throw(
				_("Set an Identifier on Project {0} before creating work items").format(self.project)
			)
		if (
			not self.flags.get("ignore_tracker_rules")
			and not get_capabilities(self.project)["can_create_items"]
		):
			frappe.throw(_("You are not allowed to create work items in Project {0}").format(self.project))

	def autoname(self) -> None:
		"""Name = <project identifier>-<5 digit series>, an independent series per project (R-01)."""
		identifier = frappe.db.get_value("Project", self.project, "tracker_identifier")
		self.name = make_autoname(f"{identifier}-.#####", "Work Item")

	# ------------------------------------------------------------------ validation
	def validate(self) -> None:
		"""Run all server-side rules for the document."""
		self.old = self.get_doc_before_save()
		self.validate_edit_permission()
		self.set_defaults()
		self.validate_tracker()
		self.validate_dates_and_numbers()
		self.validate_assignee()
		self.validate_category_and_release()
		self.validate_sprint()
		self.validate_parent()
		self.sync_client_dependency()
		self.validate_status_change()
		self.validate_relations()
		self.apply_children_progress()

	def validate_edit_permission(self) -> None:
		"""R-15: editing needs can_edit_any_item, or being the author or the assignee."""
		if self.is_new() or self.flags.get("ignore_tracker_rules"):
			return
		if get_capabilities(self.project)["can_edit_any_item"]:
			return
		if frappe.session.user in (self.old.author, self.old.assigned_to):
			return
		frappe.throw(_("You can only edit work items you created or are assigned to"))

	def set_defaults(self) -> None:
		"""R-06 default status, R-07 author, priority default from settings."""
		settings = get_settings()
		if self.is_new():
			self.author = self.flags.get("author") or frappe.session.user
			if not self.status:
				self.status = (
					frappe.db.get_value("Ticket Type", self.tracker, "default_status")
					or settings.default_status
				)
			if cint(frappe.db.get_value("Work Item Status", self.status, "is_closed")):
				frappe.throw(_("A new work item cannot start in a closed status"))
		else:
			self.author = self.old.author
		if not self.priority:
			self.priority = settings.default_priority

	def validate_tracker(self) -> None:
		"""R-05: the tracker must be active and enabled on the project."""
		if not self.is_new() and self.old.tracker == self.tracker:
			return
		if self.tracker not in get_enabled_trackers(self.project) or not cint(
			frappe.db.get_value("Ticket Type", self.tracker, "is_active")
		):
			frappe.throw(
				_("Ticket Type {0} is not enabled on Project {1}").format(self.tracker, self.project)
			)

	def validate_dates_and_numbers(self) -> None:
		"""R-09, R-10."""
		if self.start_date and self.due_date and self.due_date < self.start_date:
			frappe.throw(_("Due Date cannot be before Start Date"))
		if flt(self.estimated_hours) < 0:
			frappe.throw(_("Estimated Hours cannot be negative"))
		if not 0 <= flt(self.done_percent) <= 100:
			frappe.throw(_("% Done must be between 0 and 100"))

	def validate_assignee(self) -> None:
		"""R-11: the assignee must be an enabled project member with can_be_assigned (no manager bypass)."""
		if not self.assigned_to:
			return
		if not self.is_new() and self.old.assigned_to == self.assigned_to:
			return
		if not get_capabilities(self.project, self.assigned_to, members_only=True)["can_be_assigned"]:
			frappe.throw(
				_("{0} cannot be assigned work items in Project {1}").format(self.assigned_to, self.project)
			)

	def validate_category_and_release(self) -> None:
		"""R-12 same project, R-13 only Open releases accept (new) items."""
		for fieldname, doctype in (("category", "Work Item Category"), ("release", "Release")):
			value = self.get(fieldname)
			if value and frappe.db.get_value(doctype, value, "project") != self.project:
				frappe.throw(_("{0} does not belong to Project {1}").format(value, self.project))
		if self.release and (self.is_new() or self.old.release != self.release):
			status = frappe.db.get_value("Release", self.release, "status")
			if status != "Open":
				frappe.throw(
					_("Release {0} is {1}; only Open releases accept work items").format(self.release, status)
				)

	def validate_sprint(self) -> None:
		"""Sprint must belong to the same project; only Planned or Active sprints accept (new) items."""
		if not self.sprint:
			return
		project, status = frappe.db.get_value("Sprint", self.sprint, ["project", "status"])
		if project != self.project:
			frappe.throw(_("{0} does not belong to Project {1}").format(self.sprint, self.project))
		if (self.is_new() or self.old.sprint != self.sprint) and status == "Completed":
			frappe.throw(
				_("Sprint {0} is {1}; only Planned or Active sprints accept work items").format(
					self.sprint, status
				)
			)

	def sync_client_dependency(self) -> None:
		"""Stamp "waiting since" when a ticket becomes dependent on the client; clear it (and the note) when it stops."""
		if cint(self.dependent_on_client):
			if self.is_new() or not cint(self.old.dependent_on_client) or not self.client_dependency_since:
				self.client_dependency_since = today()
		else:
			self.client_dependency_since = None
			self.client_dependency_note = None

	def validate_parent(self) -> None:
		"""R-14: same project, no cycles, depth limit."""
		if not self.parent_work_item:
			return
		if not self.is_new() and self.old.parent_work_item == self.parent_work_item:
			return
		if frappe.db.get_value("Work Item", self.parent_work_item, "project") != self.project:
			frappe.throw(_("Parent must be in the same project"))
		if not self.is_new() and (
			self.parent_work_item == self.name or self.parent_work_item in get_descendants(self.name)
		):
			frappe.throw(_("A work item cannot be its own parent or ancestor"))
		depth = len(get_ancestors(self.parent_work_item)) + 2  # parent's depth + this item
		if not self.is_new():
			depth += get_subtree_height(self.name)
		max_depth = cint(get_settings().max_subtask_depth)
		if depth > max_depth:
			frappe.throw(_("Maximum subtask depth of {0} exceeded").format(max_depth))

	# ------------------------------------------------------------------ status workflow (R-17 .. R-23)
	def validate_status_change(self) -> None:
		"""Apply workflow, closing and done-percent rules."""
		status = frappe.db.get_value(
			"Work Item Status", self.status, ["is_closed", "default_done_percent"], as_dict=True
		)
		new_closed = bool(cint(status.is_closed))
		self.is_closed = int(new_closed)
		status_changed = self.is_new() or self.old.status != self.status
		old_closed = bool(cint(self.old.is_closed)) if not self.is_new() else False

		if not self.is_new() and status_changed:
			if not transition_allowed(self.tracker, self.old.status, self.status, self.project):
				frappe.throw(
					_("Moving from {0} to {1} is not allowed for your role on tracker {2}").format(
						self.old.status, self.status, self.tracker
					)
				)
			if new_closed:
				self.validate_can_close()
			elif old_closed:
				self.warn_if_parent_closed()

		if new_closed and not old_closed:
			self.closed_on, self.closed_by = now_datetime(), frappe.session.user
		elif not new_closed:
			self.closed_on = self.closed_by = None

		if status.default_done_percent not in (None, "") and (
			(not self.is_new() and status_changed) or (self.is_new() and not flt(self.done_percent))
		):
			self.done_percent = cint(status.default_done_percent)

	def validate_can_close(self) -> None:
		"""R-21 open children and R-22 open blockers prevent closing."""
		settings = get_settings()
		if cint(settings.require_children_closed):
			open_children = frappe.get_all(
				"Work Item", filters={"parent_work_item": self.name, "is_closed": 0}, pluck="name"
			)
			if open_children:
				frappe.throw(_("Close all subtasks first: {0}").format(", ".join(open_children)))
		if cint(settings.require_blockers_closed):
			blockers = [r.related_work_item for r in self.relations if r.relation_type == "Blocked by"]
			open_blockers = (
				frappe.get_all("Work Item", filters={"name": ["in", blockers], "is_closed": 0}, pluck="name")
				if blockers
				else []
			)
			if open_blockers:
				frappe.throw(_("This item is blocked by open items: {0}").format(", ".join(open_blockers)))

	def warn_if_parent_closed(self) -> None:
		"""R-23: reopening a child of a closed parent is allowed; tell the user."""
		if self.parent_work_item and cint(
			frappe.db.get_value("Work Item", self.parent_work_item, "is_closed")
		):
			frappe.msgprint(
				_("Parent item {0} is closed and stays closed").format(self.parent_work_item),
				indicator="orange",
			)

	def apply_children_progress(self) -> None:
		"""R-31: an item with children takes its % Done from them (R-32)."""
		if self.is_new():
			return
		children = frappe.get_all(
			"Work Item",
			filters={"parent_work_item": self.name},
			fields=["is_closed", "done_percent", "total_estimated_hours"],
		)
		if children:
			self.done_percent = compute_progress(
				[
					{
						"is_closed": c.is_closed,
						"done_percent": c.done_percent,
						"hours": c.total_estimated_hours,
					}
					for c in children
				]
			)

	# ------------------------------------------------------------------ relations (R-24 .. R-27)
	def validate_relations(self) -> None:
		"""R-25 and R-26 for the relation rows."""
		old_rows = {(r.relation_type, r.related_work_item) for r in self.old.relations} if self.old else set()
		seen: set[tuple[str, str]] = set()
		for row in self.relations:
			key = (row.relation_type, row.related_work_item)
			if row.related_work_item == self.name:
				frappe.throw(_("Cannot relate a work item to itself"))
			if key in seen:
				frappe.throw(_("This relation already exists"))
			seen.add(key)
			if key not in old_rows and frappe.db.exists("Work Item", row.related_work_item):
				if not frappe.has_permission("Work Item", "read", doc=row.related_work_item):
					frappe.throw(_("You do not have access to {0}").format(row.related_work_item))
		blocks = {t for r, t in seen if r == "Blocks"}
		blocked_by = {t for r, t in seen if r == "Blocked by"}
		for target in sorted(blocks & blocked_by):
			frappe.throw(_("{0} cannot both block and be blocked by {1}").format(self.name, target))

	def sync_relations(self) -> None:
		"""R-24: keep reciprocal rows on related items, written directly so nothing re-runs R-15/R-17."""
		old_rows = {(r.relation_type, r.related_work_item) for r in self.old.relations} if self.old else set()
		current = {(r.relation_type, r.related_work_item) for r in self.relations}
		for relation_type, target in current - old_rows:
			self.add_reverse_row(target, REVERSE_RELATION[relation_type])
		for relation_type, target in old_rows - current:
			self.remove_reverse_row(target, REVERSE_RELATION[relation_type])

	def add_reverse_row(self, target: str, reverse_type: str) -> None:
		"""Insert the reciprocal relation row on ``target`` unless it exists."""
		filters = {
			"parent": target,
			"parenttype": "Work Item",
			"parentfield": "relations",
			"relation_type": reverse_type,
			"related_work_item": self.name,
		}
		if frappe.db.exists("Work Item Relation", filters):
			return
		idx = frappe.db.sql(
			"select coalesce(max(idx), 0) from `tabWork Item Relation` where parent = %s", target
		)[0][0]
		frappe.get_doc(
			{
				"doctype": "Work Item Relation",
				**filters,
				"idx": cint(idx) + 1,
				"related_subject": self.subject,
				"related_status": self.status,
			}
		).insert(ignore_permissions=True)
		touch_modified(target)

	def remove_reverse_row(self, target: str, reverse_type: str) -> None:
		"""Delete the reciprocal relation row from ``target``."""
		frappe.db.delete(
			"Work Item Relation",
			{
				"parent": target,
				"parenttype": "Work Item",
				"parentfield": "relations",
				"relation_type": reverse_type,
				"related_work_item": self.name,
			},
		)
		touch_modified(target)

	# ------------------------------------------------------------------ after save
	def on_update(self) -> None:
		"""Assignment, relations, roll-ups and notifications."""
		self.sync_assignment()
		self.sync_relations()
		self.refresh_relation_display()
		self.update_rollups()
		self.notify_status_change()

	def sync_assignment(self) -> None:
		"""R-16: ToDo for the new assignee, close the old one, watchers for assignee and author."""
		old_assignee = self.old.assigned_to if self.old else None
		if self.assigned_to != old_assignee:
			if old_assignee:
				close_todos(self.name, old_assignee)
			if self.assigned_to:
				assign_to._add(
					{
						"doctype": "Work Item",
						"name": self.name,
						"assign_to": frappe.as_json([self.assigned_to]),
						"description": frappe.utils.escape_html(self.subject),
						"priority": TODO_PRIORITY.get(self.priority, "Medium"),
						"date": self.due_date,
					},
					ignore_permissions=True,
				)
		follow_work_item(self.name, self.assigned_to)
		follow_work_item(self.name, self.author)

	def refresh_relation_display(self) -> None:
		"""Keep the fetched subject/status of rows that point at this item current."""
		if self.old and (self.old.subject, self.old.status) == (self.subject, self.status):
			return
		frappe.db.sql(
			"update `tabWork Item Relation` set related_subject = %s, related_status = %s "
			"where related_work_item = %s",
			(self.subject, self.status, self.name),
		)

	def update_rollups(self) -> None:
		"""R-29, R-30, R-33: recalculate this item, affected ancestor chains and releases."""
		old = self.old
		recalc_chain(self.name)
		if old and old.parent_work_item and old.parent_work_item != self.parent_work_item:
			recalc_chain(old.parent_work_item)
		for release in {self.release, old.release if old else None}:
			recalc_release(release)
		for sprint in {self.sprint, old.sprint if old else None}:
			recalc_sprint(sprint)
		values = frappe.db.get_value("Work Item", self.name, [*ROLLUP_FIELDS, "modified"], as_dict=True)
		self.update(values)  # keep the in-memory document in step with the DB (assign_to bumps modified)

	def notify_status_change(self) -> None:
		"""N-2: email author and assignee about a status change, never the user who made it."""
		if not self.old or self.old.status == self.status:
			return
		recipients = {self.author, self.assigned_to} - {None, frappe.session.user}
		recipients = [u for u in recipients if frappe.db.get_value("User", u, "enabled")]
		if not recipients:
			return
		message = _("{0} changed the status of {1} ({2}) from {3} to {4}.").format(
			frappe.bold(frappe.get_cached_value("User", frappe.session.user, "full_name")),
			self.name,
			frappe.utils.escape_html(self.subject),
			self.old.status,
			self.status,
		)
		for recipient in recipients:
			safe_sendmail(
				recipients=[recipient],
				subject=_("{0}: status changed to {1}").format(self.name, self.status),
				message=message,
				reference_doctype="Work Item",
				reference_name=self.name,
			)

	# ------------------------------------------------------------------ deletion (R-37)
	def on_trash(self) -> None:
		"""R-37: capability, no children, no time entries; clean up reverse relations and ToDos."""
		if not get_capabilities(self.project)["can_delete_items"]:
			frappe.throw(_("You are not allowed to delete work items in Project {0}").format(self.project))
		if get_children(self.name):
			frappe.throw(_("Delete subtasks first"))
		if frappe.db.exists("Time Entry", {"work_item": self.name}):
			frappe.throw(_("Delete time entries on {0} first").format(self.name))
		frappe.db.delete("Work Item Relation", {"parenttype": "Work Item", "related_work_item": self.name})
		assign_to.close_all_assignments("Work Item", self.name, ignore_permissions=True)

	def after_delete(self) -> None:
		"""Recalculate the former parent chain and release."""
		recalc_chain(self.parent_work_item)
		recalc_release(self.release)
		recalc_sprint(self.sprint)


def close_todos(work_item: str, user: str) -> None:
	"""Close the open ToDos of ``user`` on ``work_item``."""
	for todo in frappe.get_all(
		"ToDo",
		filters={
			"reference_type": "Work Item",
			"reference_name": work_item,
			"allocated_to": user,
			"status": "Open",
		},
		pluck="name",
	):
		assign_to.set_status(
			"Work Item", work_item, todo=todo, assign_to=user, status="Closed", ignore_permissions=True
		)


def touch_modified(work_item: str) -> None:
	"""Bump ``modified`` so stale forms cannot overwrite a directly written relation row."""
	frappe.db.set_value("Work Item", work_item, "modified", now_datetime(), update_modified=False)


def validate_todo(doc, method: str | None = None) -> None:
	"""ToDo.validate hook: R-11 also holds for assignments made with the standard Assign To dialog."""
	if doc.reference_type != "Work Item" or doc.status != "Open" or not doc.allocated_to:
		return
	project = frappe.db.get_value("Work Item", doc.reference_name, "project")
	if project and not get_capabilities(project, doc.allocated_to, members_only=True)["can_be_assigned"]:
		frappe.throw(_("{0} cannot be assigned work items in Project {1}").format(doc.allocated_to, project))
