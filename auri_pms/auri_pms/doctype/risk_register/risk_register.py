"""Risk Register - one document per project risk, scored by probability x impact."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import cint, getdate, today

from auri_pms.auri_pms.risk import risk_level, scale_value
from auri_pms.auri_pms.utils import ensure_pms_project, has_capability


class RiskRegister(Document):
	"""A risk that may affect one project, with its assessment, owner and mitigation."""

	def before_insert(self) -> None:
		"""The project identifier is part of the name, so fetch it before naming."""
		self.set_project_identifier()

	def autoname(self) -> None:
		"""Number the risks of every project separately: ALP-RISK-0001, ALP-RISK-0002, BET-RISK-0001 ..."""
		self.set_project_identifier()
		prefix = f"{self.project_identifier}-RISK-"
		self.sync_series(prefix)
		self.name = prefix + getseries(prefix, 4)

	@staticmethod
	def sync_series(prefix: str) -> None:
		"""Lift the naming counter to the highest number in use, so a missing or stale counter cannot repeat a name."""
		used = frappe.db.sql(
			"select max(cast(substring(name, %s) as unsigned)) from `tabRisk Register` where name like %s",
			(len(prefix) + 1, f"{prefix}%"),
		)[0][0]
		used = cint(used)
		current = frappe.db.get_value("Series", prefix, "current", order_by=None)
		if current is None:
			frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s)", (prefix, used))
		elif cint(current) < used:
			frappe.db.sql("update `tabSeries` set current = %s where name = %s", (used, prefix))

	def validate(self) -> None:
		"""Capability, work item project, score and level, and the closing date."""
		self.set_project_identifier()
		self.validate_can_edit()
		self.validate_work_item()
		self.validate_dates()
		self.validate_closing()
		self.score()
		self.log_assessment()
		self.stamp_closed_on()

	def set_project_identifier(self) -> None:
		"""Copy the project identifier (needed for the document name)."""
		ensure_pms_project(self.project, _("adding risks"))
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

	def validate_closing(self) -> None:
		"""Closing a saved risk needs a remark; risks that were already closed (or are created closed) save without one."""
		if self.status != "Closed" or self.closing_remark:
			return
		old = self.get_doc_before_save()
		if old and old.status != "Closed":
			frappe.throw(_("Closing Remark is required to close a risk"), title=_("Closing Remark"))

	def validate_dates(self) -> None:
		"""A mitigation cannot be due before the risk was identified."""
		if (
			self.mitigation_due
			and self.identified_on
			and getdate(self.mitigation_due) < getdate(self.identified_on)
		):
			frappe.throw(_("Mitigation Due cannot be before Identified On"))
		if self.status == "Closed" and self.closed_on:
			if getdate(self.closed_on) > getdate(today()):
				frappe.throw(_("Closed On cannot be in the future"))
			if self.identified_on and getdate(self.closed_on) < getdate(self.identified_on):
				frappe.throw(_("Closed On cannot be before Identified On"))

	def score(self) -> None:
		"""Risk Score = probability x impact; the level follows from the score."""
		self.risk_score = scale_value(self.probability) * scale_value(self.impact)
		self.risk_level = risk_level(self.risk_score)

	def log_assessment(self) -> None:
		"""Assessed By is whoever first assessed the risk or last changed its probability or impact."""
		old = self.get_doc_before_save()
		if old and (old.probability, old.impact) == (self.probability, self.impact) and old.assessed_by:
			return
		self.assessed_by = frappe.session.user

	def stamp_closed_on(self) -> None:
		"""Closed On is the day the risk was closed; it and the closing remark are cleared when it is reopened."""
		if self.status == "Closed":
			self.closed_on = self.closed_on or today()
		else:
			self.closed_on = None
			self.closing_remark = None

	def on_trash(self) -> None:
		"""Only people who manage releases (managers and project managers) delete risks."""
		if not has_capability(self.project, "can_manage_releases"):
			frappe.throw(_("You are not allowed to delete risks in Project {0}").format(self.project))
