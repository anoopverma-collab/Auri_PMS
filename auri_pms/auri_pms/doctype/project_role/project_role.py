"""Project Role master (spec 3.5)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class ProjectRole(Document):
	"""A per-project role carrying the capability flags."""

	def onload(self) -> None:
		"""Show every Work Item field in the rules table (saved with the next save of the role)."""
		self.add_missing_field_rules()

	def add_missing_field_rules(self) -> None:
		"""Append a row (editable) for each Work Item data field the table does not list yet; drop rows of removed fields."""
		meta = frappe.get_meta("Work Item")
		names = [
			df.fieldname
			for df in meta.fields
			if df.fieldtype not in frappe.model.no_value_fields + frappe.model.table_fields
		]
		self.set("field_rules", [r for r in self.field_rules if r.field_name in names])
		listed = {r.field_name for r in self.field_rules}
		for name in names:
			if name not in listed:
				self.append("field_rules", {"field_name": name, "can_edit": 1})
		order = {n: i for i, n in enumerate(names)}
		self.field_rules.sort(key=lambda r: order[r.field_name])
		for idx, row in enumerate(self.field_rules, start=1):
			row.idx = idx
			row.field_label = _(meta.get_label(row.field_name))

	def validate(self) -> None:
		"""Check the field rules and keep the Permissions column of the list in step with the role."""
		self.validate_field_rules()
		self.add_missing_field_rules()
		text = ", ".join(
			_(df.label).removeprefix("Can ")
			for df in self.meta.fields
			if df.fieldtype == "Check" and cint(self.get(df.fieldname))
		)
		view_only = [
			_(frappe.get_meta("Work Item").get_label(r.field_name))
			for r in self.field_rules
			if not cint(r.can_edit)
		]
		self.role_permissions = f"{text} | {_('View only')}: {', '.join(view_only)}" if view_only else text

	def validate_field_rules(self) -> None:
		"""Each rule names a real Work Item data field, once."""
		meta = frappe.get_meta("Work Item")
		seen = set()
		for row in self.field_rules:
			df = meta.get_field(row.field_name)
			if not df or df.fieldtype in frappe.model.no_value_fields + frappe.model.table_fields:
				frappe.throw(_("Row {0}: {1} is not a Work Item field").format(row.idx, row.field_name))
			if row.field_name in seen:
				frappe.throw(_("Row {0}: {1} is listed twice").format(row.idx, row.field_name))
			seen.add(row.field_name)

	def on_update(self) -> None:
		"""Drop cached capabilities when a role changes."""
		from auri_pms.auri_pms.utils import clear_cache

		clear_cache()

	def on_trash(self) -> None:
		"""A role used in any Project Member row or in PMS Settings cannot be deleted."""
		if frappe.db.exists("Project Member", {"project_role": self.name}):
			frappe.throw(
				_("Project Role {0} is used by project members and cannot be deleted").format(self.name)
			)
		if frappe.db.get_single_value("PMS Settings", "public_project_role") == self.name:
			frappe.throw(
				_("Project Role {0} is used in PMS Settings and cannot be deleted").format(self.name)
			)
		if frappe.db.exists("Ticket Type Transition", {"project_role": self.name}):
			frappe.throw(
				_("Project Role {0} is used in a tracker workflow and cannot be deleted").format(self.name)
			)
