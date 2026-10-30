"""Client status report: data, email-safe HTML, PDF, emailing and the weekly schedule."""

from __future__ import annotations

import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.utils import (
	add_days,
	cint,
	flt,
	get_datetime,
	getdate,
	now_datetime,
	today,
	validate_email_address,
)

from auri_pms.auri_pms.dashboards import blocked_by_open, full_names
from auri_pms.auri_pms.health import (
	as_date,
	get_health,
	health_visible,
	module_labels,
	release_health,
	status_for_sections,
)
from auri_pms.auri_pms.risk import client_risks
from auri_pms.auri_pms.utils import get_settings, has_capability, setting
from auri_pms.permissions import can_see_project

MAX_RANGE_DAYS = 366
MAX_RECIPIENTS = 20
MAX_ATTACHMENTS = 10
MAX_EMAIL_BYTES = (
	10 * 1024 * 1024
)  # most mail servers refuse 10-25 MB messages; the database caps a row at 16 MB
BUILTIN_LAYOUT = "__builtin__"  # template value that forces the built-in layout for one send
REPORT_SECTIONS = (
	"modules",
	"delivered",
	"in_progress",
	"waiting",
	"next_up",
	"issues",
	"plan",
	"risks",
	"time",
	"created",
	"completion",
	"extra",
	"tile_delivered",  # the summary tiles, each with its own switch next to the section it counts
	"tile_open",
	"tile_overdue",
	"tile_waiting",
	"tile_time",
)
LEVEL_COLOUR = {"green": "#10b981", "amber": "#f59e0b", "red": "#ef4444", "none": "#9ca3af"}


def client_status(status: dict | None, waiting: int = 0) -> dict | None:
	"""The status as a client reads it: a plain heading and one line per area, without the score or internal figures.

	What waits on the client is listed in its own section and only counted here, as "needs your input"."""
	if not status:
		return None
	level = status["level"]
	if level in (None, "none"):  # nothing to judge yet: the report keeps saying so
		return {"label": _("No data yet"), "level": "none", "points": []}
	label = {
		"green": _("On track"),
		"amber": _("On track, with a few items to watch"),
		"red": _("Needs attention"),
	}
	lines = {  # translated when used, so the reader's language applies
		"plan": _("Some planned release or sprint dates are under pressure."),
		"issues": _("Some tickets are past their planned date."),
		"time": _("Effort is running ahead of the planned estimate."),
		"risks": _("Some project risks are being watched."),
		"in_progress": _("More work has been raised than completed recently."),
	}
	areas = []
	for reason in status["reasons"]:
		area = reason.get("section")
		if reason["level"] in ("red", "amber") and area in lines and area not in areas:
			areas.append(area)
	points = [lines[a] for a in areas]
	if level == "green":
		points = [_("There is nothing to flag in this period.")]
	if waiting:
		points.append(
			_("1 item needs your input (see below).")
			if waiting == 1
			else _("{0} items need your input (see below).").format(waiting)
		)
	return {"label": label[level], "level": level, "points": points}


def build_report(
	project: str,
	from_date,
	to_date,
	exclude: list[str] | None = None,
	include: dict | list[str] | None = None,
	ticket_notes: dict[str, str] | None = None,
) -> frappe._dict:
	"""Everything the report shows for ``project`` between two dates (permission aware).

	Tickets flagged "Hide from Client Report" and the ticket names in ``exclude`` are left out everywhere.
	The tickets in ``include`` (names, or a dict of name -> note for the client) are listed in an extra
	"Additional tickets" section whatever their state. ``ticket_notes`` (name -> note) puts a note for the client under
	those tickets wherever the report lists them."""
	if not frappe.db.exists("Project", project) or not can_see_project(project):
		frappe.throw(_("You do not have access to {0}").format(project), frappe.PermissionError)
	start, end = getdate(from_date), getdate(to_date)
	if end < start:
		frappe.throw(_("To date cannot be before From date"))
	if (end - start).days > MAX_RANGE_DAYS:
		frappe.throw(_("A report can cover at most {0} days").format(MAX_RANGE_DAYS))
	today_ = getdate(today())
	info = frappe.db.get_value(
		"Project", project, ["name", "project_name", "tracker_identifier"], as_dict=True
	)
	items = frappe.get_list(
		"Work Item",
		filters={"project": project},
		fields=[
			"name",
			"subject",
			"tracker",
			"status",
			"priority",
			"due_date",
			"is_closed",
			"creation",
			"closed_on",
			"done_percent",
			"sprint",
			"project_module",
			"estimated_hours",
			"dependent_on_client",
			"client_dependency_note",
			"client_dependency_since",
			"hide_from_client_report",
		],
		limit_page_length=0,
	)
	skipped = set(exclude or [])
	notes = include if isinstance(include, dict) else dict.fromkeys(include or [], "")
	extra = [
		frappe._dict({**i, "report_note": (notes[i.name] or "").strip()})
		for i in items
		if i.name in notes and i.name not in skipped
	]
	items = [i for i in items if not cint(i.hide_from_client_report) and i.name not in skipped]
	for item in items:
		item["client_note"] = ((ticket_notes or {}).get(item.name) or "").strip()
	entries = frappe.get_list(
		"Time Entry",
		filters={"project": project, "date": ["between", [start, end]]},
		fields=["date", "hours", "is_billable", "activity_type"],
		limit_page_length=0,
	)
	module_names = module_labels(project)
	for item in items:
		item["module"] = module_names.get(item.project_module) or ""
	statuses = frappe.get_all(
		"Work Item Status",
		filters={"is_active": 1},
		fields=["name", "sequence", "is_closed"],
		order_by="sequence asc",
	)
	open_statuses = [s.name for s in statuses if not cint(s.is_closed)]
	# "not started" is the status a new ticket begins in; without a usable default, the first open status
	default_status = frappe.db.get_single_value("PMS Settings", "default_status")
	first_open = default_status if default_status in open_statuses else next(iter(open_statuses), None)
	open_items = [i for i in items if not cint(i.is_closed)]
	in_range = lambda value: bool(value) and start <= as_date(value) <= end  # noqa: E731

	delivered = sorted(
		(i for i in items if cint(i.is_closed) and in_range(i.closed_on)),
		key=lambda i: str(i.closed_on),
		reverse=True,
	)
	created = [i for i in items if in_range(i.creation)]
	by_due = lambda i: (i.due_date is None, str(i.due_date or ""), i.name)  # noqa: E731
	in_progress = sorted((i for i in open_items if i.status != first_open), key=by_due)
	sprint_states = {
		s.name: s.status
		for s in frappe.get_all(
			"Sprint",
			filters={"project": project, "status": ["in", ["Active", "Planned"]]},
			fields=["name", "status"],
		)
	}
	horizon = end + timedelta(days=14)
	next_up = sorted(
		(
			i
			for i in open_items
			if i.status == first_open
			and (i.sprint in sprint_states or (i.due_date and getdate(i.due_date) <= horizon))
		),
		key=by_due,
	)
	waiting = sorted(
		(i for i in open_items if cint(i.dependent_on_client)),
		key=lambda i: str(i.client_dependency_since or "9999"),
	)
	overdue = sorted(
		(
			i
			for i in open_items
			if i.due_date and getdate(i.due_date) < today_ and not cint(i.dependent_on_client)
		),
		key=lambda i: str(i.due_date),
	)
	blockers = blocked_by_open(open_items)
	health = get_health(project, "3m", client_view=True)
	billable = sum(flt(e.hours) for e in entries if cint(e.is_billable))
	non_billable = sum(flt(e.hours) for e in entries if not cint(e.is_billable))
	activities: dict[str, list[float]] = {}
	for entry in entries:
		activities.setdefault(entry.activity_type, [0.0, 0.0])[0 if cint(entry.is_billable) else 1] += flt(
			entry.hours
		)

	sprint = frappe.db.get_value(
		"Sprint",
		{"project": project, "status": "Active"},
		[
			"name",
			"sprint_name",
			"start_date",
			"end_date",
			"percent_complete",
			"total_items",
			"closed_items",
			"goal",
		],
		as_dict=True,
	)
	last_sprint = frappe.db.get_value(
		"Sprint",
		{"project": project, "status": "Completed"},
		["sprint_name", "closed_items", "estimated_hours", "end_date"],
		as_dict=True,
		order_by="end_date desc",
	)
	by_module: dict[str, list[int]] = {}
	for item in items:
		if not item.module:
			continue
		row = by_module.setdefault(item.module, [0, 0])
		row[0] += 1 if cint(item.is_closed) and in_range(item.closed_on) else 0
		row[1] += 0 if cint(item.is_closed) else 1
	module_rows = [
		{"label": k, "delivered": v[0], "open": v[1]}
		for k, v in sorted(by_module.items(), key=lambda kv: (-kv[1][1], kv[0]))
	]
	total = len(items)
	return frappe._dict(
		project=info,
		from_date=start,
		to_date=end,
		generated=str(now_datetime().replace(microsecond=0)),
		status=health.status if health_visible(project, "report") else None,
		summary=frappe._dict(
			delivered=len(delivered),
			created=len(created),
			open=len(open_items),
			overdue=len(overdue),
			completion_pct=flt((total - len(open_items)) * 100 / total, 0) if total else 0,
			hours=flt(billable + non_billable, 1),
			billable=flt(billable, 1),
			non_billable=flt(non_billable, 1),
			blocked=sum(1 for i in open_items if blockers.get(i.name)),
			waiting=len(waiting),
		),
		waiting=[
			{
				**i,
				"days": (today_ - getdate(i.client_dependency_since)).days
				if i.client_dependency_since
				else 0,
			}
			for i in waiting
		],
		waiting_more=0,
		delivered=delivered,
		delivered_more=0,
		in_progress=in_progress,
		in_progress_more=0,
		next_up=next_up,
		overdue=[{**i, "days": (today_ - getdate(i.due_date)).days} for i in overdue],
		overdue_more=0,
		blocked=[
			{"name": i.name, "subject": i.subject, "blocked_by": blockers[i.name]}
			for i in open_items
			if blockers.get(i.name)
		],
		tickets=listed_tickets(
			[
				("delivered", _("Delivered"), delivered),
				("in_progress", _("In progress"), in_progress),
				("waiting", _("Waiting on you"), waiting),
				("next_up", _("Coming up next"), next_up),
				("issues", _("Overdue"), overdue),
			]
		),
		extra=sorted(extra, key=lambda i: i.name),
		modules=module_rows,
		risks=client_risks(project),
		releases=[r for r in release_health(project, today_)],
		sprint=sprint,
		last_sprint=last_sprint,
		activities=[
			{"label": k, "billable": flt(v[0], 1), "non_billable": flt(v[1], 1)}
			for k, v in sorted(activities.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))[:6]
		],
	)


def listed_tickets(groups: list[tuple[str, str, list]]) -> list[dict]:
	"""Every (section, ticket) pair the report lists, for the remove list; ``key`` is the section switch."""
	return [
		{"name": row.name, "subject": row.subject, "section": label, "key": key}
		for key, label, rows in groups
		for row in rows
	]


def visible_tickets(tickets: list[dict], switches: dict, order: list[str] | None = None) -> list[dict]:
	"""The listed tickets of the sections that are switched on, once each, in the order of the sections."""
	rank = {key: i for i, key in enumerate(order or SECTION_KEYS)}
	seen: dict[str, dict] = {}
	for ticket in sorted(tickets, key=lambda t: rank.get(t["key"], len(rank))):
		if switches.get(ticket["key"]):
			seen.setdefault(ticket["name"], ticket)
	return list(seen.values())


def _load_default_layout() -> str:
	"""The built-in layout (the first design of the report) lives with the ready-made templates."""
	path = frappe.get_app_path("auri_pms", "templates", "emails", "pms_status_report_original.html")
	# a fixed file shipped with the app; no user input is part of the path
	# nosemgrep: frappe-security-file-traversal
	with open(path, encoding="utf-8") as f:
		return f.read()


REPORT_TEMPLATE = _load_default_layout()


# The sections a layout draws, as keys; a section's label is also its option in PMS Report Section
SECTION_LABELS = {
	"modules": "Progress by module",
	"waiting": "Waiting on client",
	"delivered": "Delivered",
	"in_progress": "In progress",
	"next_up": "Coming up next",
	"extra": "Additional tickets",
	"issues": "Risks and issues",
	"plan": "Plan (sprint and releases)",
	"risks": "Risk register mitigation",
	"time": "Time spent",
}
SECTION_KEYS = tuple(SECTION_LABELS)


def clean_order(keys) -> list[str]:
	"""``keys`` without unknown or repeated entries, with every section not named added at the end."""
	seen: list[str] = []
	for key in [*(keys or []), *SECTION_KEYS]:
		if key in SECTION_LABELS and key not in seen:
			seen.append(key)
	return seen


def configured_order() -> list[str] | None:
	"""The section order saved in PMS Settings (None when the table is empty: each layout keeps its own order)."""
	label_to_key = {label: key for key, label in SECTION_LABELS.items()}
	rows = [label_to_key.get(r.section) for r in get_settings().get("report_section_order") or []]
	return clean_order(rows) if any(rows) else None


def layout_order(source: str) -> list[str]:
	"""The order a layout draws its sections in when nothing else is chosen (its ``default_order`` list)."""
	match = re.search(r"default_order\s*=\s*\[([^\]]*)\]", source)
	return clean_order(re.findall(r"[\"'](\w+)[\"']", match.group(1)) if match else [])


def report_order(source: str, order: list[str] | None = None) -> list[str]:
	"""Section order for one report: the one chosen for it, else PMS Settings, else the layout's own."""
	if order:
		return clean_order(order)
	return configured_order() or layout_order(source)


def current_order(template: str | None = None, order: list[str] | None = None) -> list[str]:
	"""The order the report will list its sections in (shown in the Sections dialog)."""
	chosen = email_template(template)
	return report_order(template_source(chosen) if chosen else REPORT_TEMPLATE, order)


def with_ticket_notes(report: frappe._dict) -> frappe._dict:
	"""A copy of ``report`` where a ticket with a note for the client shows it under its subject.

	The subject becomes escaped markup, so every layout that prints ``i.subject`` carries the note without changes."""
	from markupsafe import Markup, escape

	def noted(row):
		if not isinstance(row, dict) or not row.get("client_note"):
			return row
		html = (
			f'{escape(row.get("subject") or "")}<br><span style="font-size:12px;font-style:italic;color:#8a94a6;">'
			f"{escape(row['client_note'])}</span>"
		)
		return frappe._dict({**row, "subject": Markup(html)})

	return frappe._dict({k: [noted(r) for r in v] if isinstance(v, list) else v for k, v in report.items()})


def render_html(
	report: frappe._dict,
	note: str | None = None,
	template: str | None = None,
	sections: dict | None = None,
	order: list[str] | None = None,
) -> str:
	"""Email-safe HTML (inline styles) for ``report``; every dynamic value is escaped.

	``template`` is an Email Template name; empty uses the one chosen in PMS Settings, else the built-in
	layout, which ``BUILTIN_LAYOUT`` forces. ``sections`` switches sections on or off and ``order`` re-orders them for this render only."""
	status = report.status
	switches = section_switches(sections)
	# the status banner only counts what the report shows
	status = status_for_sections(status, switches)
	report = with_ticket_notes(frappe._dict({**report, "status": status}))
	# every figure belongs to a section; switching the section off removes its figure as well, and a tile also has its own switch
	tiles = [
		t[:4]  # the layouts take (value, label, colour, section)
		for t in [
			(report.summary.delivered, _("Delivered"), "#ecfdf5", "delivered", "tile_delivered"),
			(report.summary.created, _("New tickets"), "#eff6ff", "created", None),
			(report.summary.open, _("Open"), "#e3f2fd", "in_progress", "tile_open"),
			(
				report.summary.overdue,
				_("Overdue"),
				"#fef2f2" if report.summary.overdue else "#f9fafb",
				"issues",
				"tile_overdue",
			),
			(
				report.summary.waiting,
				_("Waiting on you"),
				"#fffbeb" if report.summary.waiting else "#f9fafb",
				"waiting",
				"tile_waiting",
			),
			(f"{report.summary.completion_pct:.0f}%", _("Complete"), "#ecfdf5", "completion", None),
			(report.summary.hours, _("Hours"), "#ecfeff", "time", "tile_time"),
		]
		if switches[t[3]] and (t[4] is None or switches[t[4]])
	]
	context = {
		"r": report,
		"note": (note or "").strip(),
		"colour": LEVEL_COLOUR.get(status["level"] if status else "none", LEVEL_COLOUR["none"]),
		"client_status": client_status(status, report.summary.waiting if switches["waiting"] else 0),
		"tiles": tiles,
		"risk_releases": [rel for rel in report.releases if rel["risk"] in ("late", "risk")],
		"show": frappe._dict(switches),
	}
	# The built-in template is a module constant. A chosen Email Template is authored by users who may
	# already edit Email Templates (Frappe renders those the same way).
	template = email_template(template)
	source = template_source(template) if template else REPORT_TEMPLATE
	context["order"] = report_order(source, order)
	return frappe.render_template(source, context)  # nosemgrep: frappe-ssti


def section_switches(overrides: dict | None = None) -> dict[str, int]:
	"""Which report sections show: the PMS Settings switches, changed by ``overrides`` for one report."""
	overrides = overrides or {}
	return {
		key: cint(overrides[key]) if key in overrides else cint(setting(f"show_report_{key}"))
		for key in REPORT_SECTIONS
	}


def email_template(name: str | None = None):
	"""The Email Template ``name``, else the one picked in PMS Settings, or None for the built-in layout."""
	if name == BUILTIN_LAYOUT:
		return None
	name = name or setting("report_email_template")
	if not name or not frappe.db.exists("Email Template", name):
		return None
	if not cint(frappe.db.get_value("Email Template", name, "auri_pms_enabled")):
		frappe.throw(_("Email Template {0} is not enabled for Auri PMS").format(name))
	return frappe.get_cached_doc("Email Template", name)


def template_source(template) -> str:
	"""The Jinja source of an Email Template: its HTML field when "Use HTML" is on, else the rich text."""
	return (template.response_html if template.use_html else template.response) or ""


def parse_recipients(raw: str | list[str]) -> list[str]:
	"""Split, validate and de-duplicate recipient addresses."""
	parts = raw if isinstance(raw, list) else re.split(r"[,;\n\s]+", raw or "")
	seen: dict[str, None] = {}
	for part in parts:
		address = (part or "").strip()
		if not address:
			continue
		if not validate_email_address(address):
			frappe.throw(_("{0} is not a valid email address").format(address))
		seen[address.lower()] = None
	addresses = list(seen)
	if not addresses:
		frappe.throw(_("Add at least one recipient"))
	if len(addresses) > MAX_RECIPIENTS:
		frappe.throw(_("At most {0} recipients are allowed").format(MAX_RECIPIENTS))
	return addresses


def parse_copies(raw: str | list[str] | None, taken: list[str]) -> list[str]:
	"""CC addresses: validated and de-duplicated like recipients, but optional, and never repeating an address in ``taken``."""
	if not raw or (isinstance(raw, str) and not raw.strip()):
		return []
	return [a for a in parse_recipients(raw) if a not in taken]


def check_attachments(names: list[str] | None) -> list:
	"""The File documents for the extra attachments of one email, after checking them.

	Only a file the sender uploaded for this email is accepted: their own, not attached to any document yet,
	and not a folder. So a form cannot be used to email someone else's file."""
	names = list(dict.fromkeys(names or []))
	if len(names) > MAX_ATTACHMENTS:
		frappe.throw(_("At most {0} attachments are allowed").format(MAX_ATTACHMENTS))
	files = []
	for name in names:
		file = frappe.get_doc("File", name) if frappe.db.exists("File", name) else None
		if (
			not file
			or file.is_folder
			or file.owner != frappe.session.user
			or file.attached_to_doctype
			or file.attached_to_name
		):
			frappe.throw(_("{0} cannot be attached to this email").format(name))
		files.append(file)
	return files


def merge_recipients(*lists: str | None) -> str:
	"""Several recipient lists as one comma separated string, without repeats (case-insensitive)."""
	seen: dict[str, str] = {}
	for raw in lists:
		for part in re.split(r"[,;\n\s]+", raw or ""):
			if part.strip():
				seen.setdefault(part.strip().lower(), part.strip())
	return ", ".join(seen.values())


def default_subject(report: frappe._dict, template: str | None = None) -> str:
	"""Default email subject: the Email Template subject when one is chosen, else the built-in one."""
	template = email_template(template)
	if not (template and template.subject) and setting("report_default_subject"):
		return (
			setting("report_default_subject")
			.replace("{project}", report.project.project_name or "")
			.replace("{from_date}", frappe.utils.formatdate(report.from_date))
			.replace("{to_date}", frappe.utils.formatdate(report.to_date))
		)[:140]
	if template and template.subject:
		# the subject belongs to an Email Template that is enabled for Auri PMS (written by users who may edit Email Templates)
		# nosemgrep: frappe-ssti
		return frappe.render_template(template.subject, {"r": report, "report": report})
	return _("{0}: status report {1} to {2}").format(
		report.project.project_name,
		frappe.utils.formatdate(report.from_date),
		frappe.utils.formatdate(report.to_date),
	)


def send_report(
	project: str,
	from_date,
	to_date,
	recipients,
	subject: str | None = None,
	note: str | None = None,
	scheduled: bool = False,
	cc=None,
	exclude: list[str] | None = None,
	template: str | None = None,
	include: dict | list[str] | None = None,
	sections: dict | None = None,
	order: list[str] | None = None,
	ticket_notes: dict[str, str] | None = None,
	attachments: list[str] | None = None,
) -> str:
	"""Email the report and log it as a Project Status Report. Returns the log document name.

	``attachments`` are File names the sender uploaded for this email (see ``check_attachments``)."""
	if not has_capability(project, "can_manage_releases"):
		frappe.throw(_("You are not allowed to send status reports for Project {0}").format(project))
	addresses = parse_recipients(recipients)
	cc_addresses = parse_copies(cc, addresses)
	if len(addresses) + len(cc_addresses) > MAX_RECIPIENTS:
		frappe.throw(_("At most {0} recipients are allowed").format(MAX_RECIPIENTS))
	# Frappe only notices a missing outgoing account when the queue sends; tell the user now instead of "sending" nothing.
	EmailAccount.find_outgoing(_raise_error=True)
	report = build_report(project, from_date, to_date, exclude, include, ticket_notes)
	html = render_html(report, note, template, sections, order)
	files = check_attachments(attachments)
	size = len(html.encode("utf-8")) + sum(f.file_size or 0 for f in files)
	if size > MAX_EMAIL_BYTES:
		frappe.throw(
			_(
				"This report with its attachments is {0} MB, which is too large to email. Switch off some sections, remove tickets or attachments, or use a shorter period."
			).format(round(size / 1024 / 1024, 1))
		)
	subject = (subject or default_subject(report, template))[:140]
	values = {
		"doctype": "Project Status Report",
		"subject": subject,
		"project": project,
		"from_date": report.from_date,
		"to_date": report.to_date,
		"status_level": report.status.level if report.status else "",
		"sent_on": now_datetime(),
		"sent_by": frappe.session.user,
		"scheduled": 1 if scheduled else 0,
		"sent_to": ", ".join(addresses),
		"sent_cc": ", ".join(cc_addresses),
		"recipient_count": len(addresses) + len(cc_addresses),
		"delivery_status": "Queued",
		"body": html,
	}

	log = frappe.get_doc(values).insert(ignore_permissions=True)
	for file in files:  # the files show in the attachments of the Status Reports Sent record
		file.attached_to_doctype, file.attached_to_name = log.doctype, log.name
		file.save(ignore_permissions=True)
	try:
		# the queue entries point at the log so their delivery state can be read back later
		frappe.sendmail(
			recipients=addresses,
			cc=cc_addresses,
			subject=subject,
			message=html,
			attachments=[{"fid": f.name} for f in files],
			reference_doctype=log.doctype,
			reference_name=log.name,
			add_unsubscribe_link=0,
		)
	except Exception as e:
		# keep a record of the failed attempt even though the request is rolled back
		frappe.db.rollback()
		frappe.get_doc(
			# without the body: the failure may be that the message is too large to store
			{
				**values,
				"body": "",
				"delivery_status": "Failed",
				"failed_count": len(addresses) + len(cc_addresses),
				"error": str(e)[:500],
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()
		raise
	return log.name


def get_pdf_bytes(
	project: str,
	from_date,
	to_date,
	note: str | None = None,
	exclude: list[str] | None = None,
	template: str | None = None,
	include: dict | list[str] | None = None,
	sections: dict | None = None,
	order: list[str] | None = None,
	ticket_notes: dict[str, str] | None = None,
) -> bytes:
	"""PDF of the report (wkhtmltopdf through Frappe), laid out to fill an A4 page."""
	import pdfkit
	from frappe.utils.pdf import scrub_urls

	html = render_html(
		build_report(project, from_date, to_date, exclude, include, ticket_notes),
		note,
		template,
		sections,
		order,
	)
	# Frappe's get_pdf forces 15mm top and bottom margins (white paper); call wkhtmltopdf directly so
	# the colour behind the report reaches the edges of the sheet
	pdf = pdfkit.from_string(scrub_urls(fit_to_page(html)), options=PDF_OPTIONS)
	return paint_sheets(pdf, sheet_colour(html))


# The email layouts are 600-700px wide; on paper that left a narrow strip of small text.
PDF_OPTIONS = {
	"page-size": "A4",
	# no paper margin: wkhtmltopdf leaves it white, so the report paints its own 0.2in spacing instead
	"margin-top": "0",
	"margin-bottom": "0",
	"margin-left": "0",
	"margin-right": "0",
	"zoom": "1.2",
	"encoding": "UTF-8",
	"quiet": None,
	"background": None,
	"disable-javascript": "",
	"disable-local-file-access": "",
}


def page_colours(html: str) -> tuple[str | None, str | None]:
	"""The page colour (the report's outermost background) and the card colour on top of it."""
	colours = re.findall(r"background:\s*(#[0-9a-fA-F]{6})", html)
	return (colours[0] if colours else None), (colours[1] if len(colours) > 1 else None)


def sheet_colour(html: str) -> str | None:
	"""The colour painted behind every sheet: the card colour (the page colour when there is no card)."""
	page, card = page_colours(html)
	return card or page


def paint_sheets(pdf: bytes, colour: str | None) -> bytes:
	"""Put ``colour`` behind every sheet. wkhtmltopdf paints only up to the end of the content, which left
	the foot of the last sheet white next to a dark or tinted report."""
	if not colour:
		return pdf
	import io

	from pypdf import PageObject, PdfReader, PdfWriter
	from pypdf.generic import DecodedStreamObject, NameObject

	red, green, blue = (int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
	writer = PdfWriter()
	for page in PdfReader(io.BytesIO(pdf)).pages:
		width, height = float(page.mediabox.width), float(page.mediabox.height)
		sheet = writer.add_page(PageObject.create_blank_page(None, width, height))
		fill = DecodedStreamObject()
		fill.set_data(f"{red:.4f} {green:.4f} {blue:.4f} rg 0 0 {width} {height} re f".encode())
		sheet[NameObject("/Contents")] = writer._add_object(fill)
		sheet.merge_page(page)
	out = io.BytesIO()
	writer.write(out)
	return out.getvalue()


def fit_to_page(html: str) -> str:
	"""Full-bleed layout for paper: the card colour fills the sheet; there is no page colour, frame or margin."""
	html = re.sub(r"max-width:\s*\d+px", "max-width:100%", html)
	html = re.sub(r"margin:\s*0 auto", "margin:0", html)
	html = re.sub(r"border-radius:\s*\d+px", "border-radius:0", html)
	# the outer wrapper (page colour and padding) and the card's frame go
	html = re.sub(r"(<div style=\"[^\"]*?)padding:\s*\d+px \d+px;", r"\1padding:0;", html, count=1)
	html = re.sub(r"(<table[^>]*style=\"[^\"]*?)border:1px solid #[0-9a-fA-F]{3,6};", r"\1", html, count=1)
	# wkhtmltopdf's old WebKit draws modern gradients as banded blocks; the solid colour beside it is kept
	html = re.sub(r"background-image:\s*linear-gradient\([^)]*\);?", "", html)
	page, card = page_colours(html)
	colour = card or page  # the card colour is the one kept; the page colour behind it goes
	if page and card and card != page:
		html = html.replace(f"background:{page}", "background:transparent", 1)
	paper = f"html, body {{ background: {colour}; }} " if colour else ""
	return (
		'<meta charset="utf-8"><style>'
		+ paper
		+ "tr, td, th, .keep { page-break-inside: avoid; } body { margin: 0; }"
		" @media print { body { -webkit-print-color-adjust: exact; } }</style>" + html
	)


def send_scheduled_reports() -> None:
	"""Daily job: send the weekly report on the chosen weekday and the monthly report on the chosen day (or both)."""
	today_ = getdate(today())
	first_of_month = today_.replace(day=1)
	last_month_end = add_days(first_of_month, -1)
	due = [
		# weekly: the previous 7 days
		(
			{"tracker_report_weekday": today_.strftime("%A")},
			add_days(today_, -7),
			add_days(today_, -1),
		),
		# monthly: the previous calendar month (a project can have both)
		(
			{"tracker_report_month_day": str(today_.day)},
			last_month_end.replace(day=1),
			last_month_end,
		),
	]
	for filters, from_date, to_date in due:
		projects = frappe.get_all(
			"Project",
			filters={**filters, "pms_enabled": 1, "tracker_report_recipients": ["is", "set"]},
			fields=["name", "tracker_report_recipients", "tracker_report_cc"],
		)
		for project in projects:
			# once per report period: a weekly and a monthly report may go out on the same day
			already = frappe.db.exists(
				"Project Status Report",
				{
					"project": project.name,
					"scheduled": 1,
					"from_date": str(from_date),
					"to_date": str(to_date),
					"sent_on": [">=", get_datetime(f"{today_} 00:00:00")],
				},
			)
			if already:
				continue
			try:
				send_report(
					project.name,
					from_date,
					to_date,
					merge_recipients(project.tracker_report_recipients, setting("report_default_recipients")),
					scheduled=True,
					cc=merge_recipients(project.tracker_report_cc, setting("report_default_cc")),
				)
			except Exception:
				frappe.log_error(title=f"Auri PMS: scheduled status report failed for {project.name}")
