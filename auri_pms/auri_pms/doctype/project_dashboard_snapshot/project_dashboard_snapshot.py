# Copyright (c) 2026, Anoop Verma and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ProjectDashboardSnapshot(Document):
	"""The Project Health dashboard of one project as it stood on one day, kept for history and comparison."""

	def before_insert(self) -> None:
		"""Snapshots are written by the system; only an admin may create one by hand."""
		check_system_record(self)


def check_system_record(doc) -> None:
	"""Records made by a job or a report action are saved with ignore_permissions; anyone else needs an admin role."""
	from auri_pms.auri_pms.utils import is_admin

	if not doc.flags.ignore_permissions and not is_admin():
		frappe.throw(
			_("{0} records are created by the system").format(_(doc.doctype)), frappe.PermissionError
		)
