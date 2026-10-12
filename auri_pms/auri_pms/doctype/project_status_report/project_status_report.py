"""Project Status Report - a log of every client status report that was emailed."""

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime

OPEN_STATUSES = ("Queued", "Partially Sent")


class ProjectStatusReport(Document):
	"""A sent (or scheduled) client status report with the exact HTML that went out and what happened to each email."""

	def onload(self) -> None:
		"""Show the current delivery state when an unfinished report is opened."""
		if self.delivery_status in OPEN_STATUSES:
			self.refresh_delivery_status()

	def refresh_delivery_status(self) -> None:
		"""Count delivered and failed recipients from the Email Queue entries of this report."""
		queues = frappe.get_all(
			"Email Queue",
			filters={"reference_doctype": self.doctype, "reference_name": self.name},
			pluck="name",
		)
		if not queues:
			return  # entries are purged after a while; keep the last known state
		statuses = frappe.get_all("Email Queue Recipient", filters={"parent": ["in", queues]}, pluck="status")
		sent, failed = statuses.count("Sent"), statuses.count("Error")
		if not statuses:
			return
		if sent == len(statuses):
			status = "Sent"
		elif sent + failed == len(statuses):
			status = "Failed" if not sent else "Partially Sent"
		else:
			status = "Partially Sent" if sent or failed else "Queued"
		if (sent, failed, status) != (self.sent_count, self.failed_count, self.delivery_status):
			self.db_set({"sent_count": sent, "failed_count": failed, "delivery_status": status})


def refresh_pending_statuses() -> None:
	"""Hourly job: update reports of the last 14 days whose emails were not all delivered yet."""
	for name in frappe.get_all(
		"Project Status Report",
		filters={"delivery_status": ["in", OPEN_STATUSES], "creation": [">=", add_days(now_datetime(), -14)]},
		pluck="name",
	):
		frappe.get_doc("Project Status Report", name).refresh_delivery_status()
