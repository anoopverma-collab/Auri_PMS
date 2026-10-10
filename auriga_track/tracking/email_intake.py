"""Optional email intake (R-40): turn received emails on a mapped Email Account into Work Items."""

from __future__ import annotations

import re

import frappe
from frappe import _

TAG_PATTERN = re.compile(r"\[([A-Z][A-Z0-9]{1,9}-\d{5})\]")


def on_communication(doc, method: str | None = None) -> None:
	"""Communication.after_insert hook."""
	if doc.communication_type != "Communication" or doc.sent_or_received != "Received":
		return
	if doc.reference_doctype or not doc.email_account:
		return
	project, default_tracker = frappe.db.get_value(
		"Email Account", doc.email_account, ["tracker_project", "tracker_default_tracker"]
	) or (None, None)
	if not project:
		return

	tag = TAG_PATTERN.search(doc.subject or "")
	if tag and frappe.db.exists("Work Item", tag.group(1)):
		link_communication(doc, tag.group(1))
		return
	try:
		item = create_work_item(doc, project, default_tracker)
	except Exception:
		frappe.log_error(title=_("Auri PMS email intake failed"))
		return
	link_communication(doc, item.name)


def create_work_item(doc, project: str, tracker: str | None):
	"""Create the Work Item for a received email."""
	sender = frappe.utils.parse_addr(doc.sender)[1] or doc.sender
	author = frappe.db.get_value("User", {"email": sender, "enabled": 1}, "name") or "Administrator"
	item = frappe.get_doc(
		{
			"doctype": "Work Item",
			"subject": (doc.subject or _("(no subject)"))[:255],
			"description": doc.content,
			"project": project,
			"tracker": tracker or default_intake_tracker(),
			"raised_by_email": sender,
		}
	)
	item.flags.author = author
	item.flags.ignore_tracker_rules = True
	item.insert(ignore_permissions=True)
	return item


def default_intake_tracker() -> str | None:
	"""Support if it exists, else the first active tracker."""
	if frappe.db.get_value("Ticket Type", "Support", "is_active"):
		return "Support"
	return frappe.db.get_value("Ticket Type", {"is_active": 1}, "name", order_by="name asc")


def link_communication(doc, work_item: str) -> None:
	"""Link the Communication to the Work Item so it shows in the item's timeline."""
	frappe.db.set_value(
		"Communication",
		doc.name,
		{"reference_doctype": "Work Item", "reference_name": work_item},
		update_modified=False,
	)
	doc.reference_doctype, doc.reference_name = "Work Item", work_item
