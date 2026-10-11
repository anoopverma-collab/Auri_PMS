"""Risk Register - one document per project risk, scored by probability x impact."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import getdate, today

from auri_pms.auri_pms.risk import risk_level, scale_value
from auri_pms.auri_pms.utils import has_capability


class RiskRegister(Document):
	"""A risk that may affect one project, with its assessment, owner and mitigation."""

	def before_insert(self) -> None:
		"""The project identifier is part of the name, so fetch it before naming."""
		self.set_project_identifier()

	def autoname(self) -> None:
		"""Number the risks of every project separately: ALP-RISK-0001, ALP-RISK-0002, BET-RISK-0001 ..."""
		self.set_project_identifier()
		prefix = f"{self.project_identifier}-RISK-"
		self.name = prefix + getseries(prefix, 4)

	def validate(self) -> None:
		"""Capability, work item project, score and level, and the closing date."""
		self.set_project_identifier()
		self.validate_can_edit()
		self.validate_work_item()
		self.validate_dates()
		self.score()
		self.stamp_closed_on()

	def set_project_identifier(self) -> None:
		"""Copy the project identifier (needed for the document name)."""
		identifier = frappe.db.get_value("Project", self.project, "tracker_identifier")
		if not identifier:
			frappe.throw(_("Set an Identifier on Project {0} before adding risks").format(self.project))
		self.project_identifier = identifier

	def validate_can_edit(self) -> None:
		"""Members who may create work items (and managers) raise and edit risks."""
		if not has_capability(self.project, "can_create_items"):
			frappe.throw(_("You are not allowed to manage risks in Project {0}").format(self.project))

	def validate_work_item(self) -> None:
		"""The related work item must belong to the same project."""
		if (
			self.related_work_item
			and frappe.db.get_value("Work Item", self.related_work_item, "project") != self.project
		):
			frappe.throw(
				_("Work Item {0} does not belong to Project {1}").format(self.related_work_item, self.project)
			)

	def validate_dates(self) -> None:
		"""A mitigation cannot be due before the risk was identified."""
		if (
			self.mitigation_due
			and self.identified_on
			and getdate(self.mitigation_due) < getdate(self.identified_on)
		):
			frappe.throw(_("Mitigation Due cannot be before Identified On"))

	def score(self) -> None:
		"""Risk Score = probability x impact; the level follows from the score."""
		self.risk_score = scale_value(self.probability) * scale_value(self.impact)
		self.risk_level = risk_level(self.risk_score)

	def stamp_closed_on(self) -> None:
		"""Closed On is the day the risk was closed and is cleared when it is reopened."""
		if self.status == "Closed":
			self.closed_on = self.closed_on or today()
		else:
			self.closed_on = None

	def on_trash(self) -> None:
		"""Only people who manage releases (managers and project managers) delete risks."""
		if not has_capability(self.project, "can_manage_releases"):
			frappe.throw(_("You are not allowed to delete risks in Project {0}").format(self.project))
