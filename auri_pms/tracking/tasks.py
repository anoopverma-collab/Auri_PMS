"""Scheduler jobs (R-45)."""

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today

from auri_pms.tracking.utils import get_settings, safe_sendmail


def send_due_digests() -> None:
	"""R-45: one email per assignee listing open items due within due_reminder_days or already overdue."""
	cutoff = add_days(today(), cint(get_settings().due_reminder_days))
	items = frappe.get_all(
		"Work Item",
		filters={"is_closed": 0, "assigned_to": ["is", "set"], "due_date": ["<=", cutoff]},
		fields=["name", "subject", "project", "due_date", "priority", "status", "assigned_to"],
		order_by="due_date asc",
	)
	by_user: dict[str, list] = defaultdict(list)
	for item in items:
		by_user[item.assigned_to].append(item)
	for user, user_items in by_user.items():
		if not frappe.db.get_value("User", user, "enabled"):
			continue
		send_digest(user, user_items)


def send_digest(user: str, items: list) -> None:
	"""Queue a single digest email for ``user``."""
	rows = "".join(
		"<tr><td><a href='{url}'>{name}</a></td><td>{subject}</td><td>{project}</td><td>{due}</td><td>{state}</td></tr>".format(
			url=frappe.utils.get_url_to_form("Work Item", i.name),
			name=i.name,
			subject=frappe.utils.escape_html(i.subject),
			project=frappe.utils.escape_html(i.project),
			due=i.due_date,
			state=_("Overdue") if getdate(i.due_date) < getdate(today()) else _("Due soon"),
		)
		for i in items
	)
	safe_sendmail(
		recipients=[user],
		subject=_("Work items due: {0}").format(len(items)),
		message=(
			f"<p>{_('These work items assigned to you are due soon or overdue:')}</p>"
			f"<table class='table table-bordered'><tr><th>{_('Item')}</th><th>{_('Subject')}</th>"
			f"<th>{_('Project')}</th><th>{_('Due Date')}</th><th></th></tr>{rows}</table>"
		),
	)
