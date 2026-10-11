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

from auri_pms.permissions import can_see_project
from auri_pms.tracking.dashboards import blocked_by_open, full_names
from auri_pms.tracking.health import as_date, get_health, health_visible, module_labels, release_health
from auri_pms.tracking.risk import client_risks
from auri_pms.tracking.utils import has_capability

MAX_RANGE_DAYS = 366
MAX_RECIPIENTS = 20
LEVEL_COLOUR = {"green": "#10b981", "amber": "#f59e0b", "red": "#ef4444", "none": "#9ca3af"}


def build_report(project: str, from_date, to_date) -> frappe._dict:
	"""Everything the report shows for ``project`` between two dates (permission aware)."""
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
		],
		limit_page_length=0,
	)
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
		"Work Item Status", fields=["name", "sequence", "is_closed"], order_by="sequence asc"
	)
	first_open = next((s.name for s in statuses if not cint(s.is_closed)), None)
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
	health = get_health(project, "3m")
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
			for i in waiting[:15]
		],
		waiting_more=max(len(waiting) - 15, 0),
		delivered=delivered[:40],
		delivered_more=max(len(delivered) - 40, 0),
		in_progress=in_progress[:30],
		in_progress_more=max(len(in_progress) - 30, 0),
		next_up=next_up[:15],
		overdue=[{**i, "days": (today_ - getdate(i.due_date)).days} for i in overdue[:10]],
		overdue_more=max(len(overdue) - 10, 0),
		blocked=[
			{"name": i.name, "subject": i.subject, "blocked_by": blockers[i.name]}
			for i in open_items
			if blockers.get(i.name)
		][:10],
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


REPORT_TEMPLATE = """
<div style="background:#f3f4f6;padding:24px 8px;font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;color:#1f2937;">
<table role="presentation" cellpadding="0" cellspacing="0" style="max-width:720px;margin:0 auto;background:#ffffff;border-radius:10px;overflow:hidden;width:100%;">
<tr><td style="background:#1e1b4b;color:#ffffff;padding:22px 28px;">
  <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.75;">{{ _("Project status report") }}</div>
  <div style="font-size:24px;font-weight:700;margin-top:4px;">{{ r.project.project_name | e }} <span style="font-size:13px;font-weight:600;background:rgba(255,255,255,.18);border-radius:999px;padding:3px 10px;vertical-align:middle;">{{ r.project.tracker_identifier | e }}</span></div>
  <div style="font-size:13px;opacity:.85;margin-top:6px;">{{ frappe.utils.formatdate(r.from_date) }} &ndash; {{ frappe.utils.formatdate(r.to_date) }}</div>
</td></tr>
{% if r.status %}<tr><td style="padding:22px 28px 6px;">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="border:1px solid #e5e7eb;border-left:6px solid {{ colour }};border-radius:8px;"><tr>
    <td style="padding:14px 16px;">
      <div style="font-size:20px;font-weight:700;color:{{ colour }};">{{ r.status.label | e }}{% if r.status.score is not none %} <span style="font-size:13px;color:#6b7280;font-weight:600;">&middot; {{ _("score") }} {{ r.status.score }}/100</span>{% endif %}</div>
      {% for reason in r.status.reasons %}<div style="font-size:13px;margin-top:4px;color:#374151;">&bull; {{ reason.text | e }}</div>{% endfor %}
    </td></tr></table>
</td></tr>{% endif %}
{% if note %}<tr><td style="padding:14px 28px 0;"><div style="background:#eef2ff;border-radius:8px;padding:12px 16px;font-size:14px;line-height:1.5;">{{ note | e | replace("\\n", "<br>") | safe }}</div></td></tr>{% endif %}
<tr><td style="padding:18px 28px 0;">
  <table role="presentation" cellpadding="0" cellspacing="6" width="100%"><tr>
    {% for value, label, tint in tiles %}<td align="center" style="background:{{ tint }};border-radius:8px;padding:12px 4px;"><div style="font-size:22px;font-weight:700;">{{ value }}</div><div style="font-size:11px;color:#6b7280;">{{ label | e }}</div></td>{% endfor %}
  </tr></table>
</td></tr>
{% macro section(title) %}<tr><td style="padding:22px 28px 4px;"><div style="font-size:15px;font-weight:700;border-bottom:2px solid #e5e7eb;padding-bottom:6px;">{{ title | e }}</div></td></tr>{% endmacro %}
{% macro th(text) %}<th align="left" style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#6b7280;padding:6px 6px;border-bottom:1px solid #e5e7eb;">{{ text | e }}</th>{% endmacro %}
{% macro tdm(text, module) %}<td style="font-size:13px;padding:6px;border-bottom:1px solid #f3f4f6;">{{ text | e }}{% if module %}<div style="font-size:11px;color:#6b7280;">{{ module | e }}</div>{% endif %}</td>{% endmacro %}
{% macro td(text, extra="") %}<td style="font-size:13px;padding:6px;border-bottom:1px solid #f3f4f6;{{ extra }}">{{ text | e }}</td>{% endmacro %}

{% if r.modules %}{{ section(_("Progress by module")) }}
<tr><td style="padding:6px 28px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{{ th(_("Module")) }}{{ th(_("Delivered")) }}{{ th(_("Open")) }}</tr>
{% for m in r.modules %}<tr>{{ td(m.label) }}{{ td(m.delivered) }}{{ td(m.open) }}</tr>{% endfor %}</table></td></tr>{% endif %}

{{ section(_("Delivered in this period") + " (" ~ r.summary.delivered ~ ")") }}
<tr><td style="padding:6px 28px;">{% if r.delivered %}<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{{ th(_("Ticket")) }}{{ th(_("Summary")) }}{{ th(_("Type")) }}{{ th(_("Closed")) }}</tr>
{% for i in r.delivered %}<tr>{{ td(i.name, "white-space:nowrap;") }}{{ tdm(i.subject, i.module) }}{{ td(i.tracker) }}{{ td(frappe.utils.formatdate(i.closed_on)) }}</tr>{% endfor %}</table>{% if r.delivered_more %}<div style="font-size:12px;color:#6b7280;padding:6px;">+ {{ r.delivered_more }} {{ _("more") }}</div>{% endif %}{% else %}<div style="font-size:13px;color:#6b7280;padding:6px;">{{ _("No tickets were closed in this period.") }}</div>{% endif %}</td></tr>

{{ section(_("In progress") + " (" ~ (r.in_progress | length + r.in_progress_more) ~ ")") }}
<tr><td style="padding:6px 28px;">{% if r.in_progress %}<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{{ th(_("Ticket")) }}{{ th(_("Summary")) }}{{ th(_("Status")) }}{{ th(_("% done")) }}{{ th(_("Due")) }}</tr>
{% for i in r.in_progress %}<tr>{{ td(i.name, "white-space:nowrap;") }}{{ tdm(i.subject, i.module) }}{{ td(i.status) }}{{ td(i.done_percent | int ~ "%") }}{{ td(frappe.utils.formatdate(i.due_date) if i.due_date else "") }}</tr>{% endfor %}</table>{% if r.in_progress_more %}<div style="font-size:12px;color:#6b7280;padding:6px;">+ {{ r.in_progress_more }} {{ _("more") }}</div>{% endif %}{% else %}<div style="font-size:13px;color:#6b7280;padding:6px;">{{ _("Nothing is in progress right now.") }}</div>{% endif %}</td></tr>

{% if r.waiting %}{{ section(_("Waiting on you") + " (" ~ r.summary.waiting ~ ")") }}
<tr><td style="padding:6px 28px;"><div style="font-size:12px;color:#6b7280;padding:2px 6px 6px;">{{ _("These tickets cannot move forward until we receive your input.") }}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{{ th(_("Ticket")) }}{{ th(_("Summary")) }}{{ th(_("What we need")) }}{{ th(_("Waiting")) }}</tr>
{% for i in r.waiting %}<tr>{{ td(i.name, "white-space:nowrap;") }}{{ tdm(i.subject, i.module) }}{{ td(i.client_dependency_note or "") }}{{ td(i.days ~ " " ~ _("days"), "color:#b45309;white-space:nowrap;") }}</tr>{% endfor %}</table>{% if r.waiting_more %}<div style="font-size:12px;color:#6b7280;padding:6px;">+ {{ r.waiting_more }} {{ _("more") }}</div>{% endif %}</td></tr>{% endif %}

{% if r.next_up %}{{ section(_("Coming up next")) }}
<tr><td style="padding:6px 28px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{{ th(_("Ticket")) }}{{ th(_("Summary")) }}{{ th(_("Priority")) }}{{ th(_("Due")) }}</tr>
{% for i in r.next_up %}<tr>{{ td(i.name, "white-space:nowrap;") }}{{ tdm(i.subject, i.module) }}{{ td(i.priority) }}{{ td(frappe.utils.formatdate(i.due_date) if i.due_date else "") }}</tr>{% endfor %}</table></td></tr>{% endif %}

{% if r.overdue or r.blocked or risk_releases %}{{ section(_("Risks and issues")) }}
<tr><td style="padding:6px 28px;">
{% if r.overdue %}<div style="font-size:13px;font-weight:600;padding:4px 6px;">{{ _("Overdue tickets") }} ({{ r.summary.overdue }})</div><table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{% for i in r.overdue %}<tr>{{ td(i.name, "white-space:nowrap;") }}{{ tdm(i.subject, i.module) }}{{ td(i.days ~ " " ~ _("days late"), "color:#ef4444;white-space:nowrap;") }}</tr>{% endfor %}</table>{% if r.overdue_more %}<div style="font-size:12px;color:#6b7280;padding:6px;">+ {{ r.overdue_more }} {{ _("more") }}</div>{% endif %}{% endif %}
{% if r.blocked %}<div style="font-size:13px;font-weight:600;padding:10px 6px 4px;">{{ _("Blocked tickets") }}</div><table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{% for i in r.blocked %}<tr>{{ td(i.name, "white-space:nowrap;") }}{{ tdm(i.subject, i.module) }}{{ td(_("waiting for") ~ " " ~ i.blocked_by | join(", ")) }}</tr>{% endfor %}</table>{% endif %}
{% for rel in risk_releases %}<div style="font-size:13px;padding:8px 6px 0;color:#b45309;">&#9888; {{ _("Release") }} {{ rel.label | e }}: {{ rel.percent | int }}% {{ _("complete") }}{% if rel.days_left is not none %}, {% if rel.days_left < 0 %}{{ -rel.days_left }} {{ _("days past due") }}{% else %}{{ rel.days_left }} {{ _("days left") }}{% endif %}{% endif %}</div>{% endfor %}
</td></tr>{% endif %}

{% if r.sprint or r.releases %}{{ section(_("Plan")) }}
<tr><td style="padding:6px 28px;">
{% if r.sprint %}<div style="font-size:13px;padding:4px 6px;"><b>{{ _("Current sprint") }}:</b> {{ r.sprint.sprint_name | e }} ({{ frappe.utils.formatdate(r.sprint.start_date) }} &ndash; {{ frappe.utils.formatdate(r.sprint.end_date) }}) &middot; {{ r.sprint.closed_items }}/{{ r.sprint.total_items }} {{ _("tickets closed") }} ({{ r.sprint.percent_complete | int }}%){% if r.sprint.goal %}<br><span style="color:#6b7280;">{{ _("Goal") }}: {{ r.sprint.goal | e }}</span>{% endif %}</div>{% endif %}
{% if r.last_sprint %}<div style="font-size:13px;padding:4px 6px;"><b>{{ _("Last completed sprint") }}:</b> {{ r.last_sprint.sprint_name | e }} &middot; {{ r.last_sprint.closed_items }} {{ _("tickets delivered") }}</div>{% endif %}
{% if r.releases %}<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:6px;"><tr>{{ th(_("Release")) }}{{ th(_("Due")) }}{{ th(_("Progress")) }}</tr>
{% for rel in r.releases %}<tr>{{ td(rel.label) }}{{ td(frappe.utils.formatdate(rel.due_date) if rel.due_date else "") }}{{ td(rel.percent | int ~ "%") }}</tr>{% endfor %}</table>{% endif %}
</td></tr>{% endif %}

{% if r.risks %}{{ section(_("Risks and mitigation") + " (" ~ r.risks | length ~ ")") }}
<tr><td style="padding:6px 28px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{{ th(_("Risk")) }}{{ th(_("Level")) }}{{ th(_("Mitigation")) }}{{ th(_("Due")) }}</tr>
{% for k in r.risks %}<tr>{{ td(k.title) }}{{ td(k.risk_level) }}{{ td(k.mitigation) }}{{ td(frappe.utils.formatdate(k.mitigation_due) if k.mitigation_due else "") }}</tr>{% endfor %}</table></td></tr>{% endif %}

{{ section(_("Time spent in this period")) }}
<tr><td style="padding:6px 28px 4px;">
<div style="font-size:13px;padding:4px 6px;">{{ r.summary.hours }} {{ _("hours in total") }} &middot; <span style="color:#059669;">{{ r.summary.billable }} {{ _("billable") }}</span> &middot; <span style="color:#b45309;">{{ r.summary.non_billable }} {{ _("non-billable") }}</span></div>
{% if r.activities %}<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{% for a in r.activities %}<tr>{{ td(a.label) }}{{ td(a.billable ~ " h " ~ _("billable")) }}{{ td(a.non_billable ~ " h " ~ _("non-billable")) }}</tr>{% endfor %}</table>{% endif %}
</td></tr>
<tr><td style="padding:22px 28px;font-size:11px;color:#9ca3af;border-top:1px solid #f3f4f6;margin-top:16px;">{{ _("Generated by Auri PMS on") }} {{ r.generated }}</td></tr>
</table></div>
"""


def render_html(report: frappe._dict, note: str | None = None) -> str:
	"""Email-safe HTML (inline styles) for ``report``; every dynamic value is escaped."""
	status = report.status
	tiles = [
		(report.summary.delivered, _("Delivered"), "#ecfdf5"),
		(report.summary.created, _("New tickets"), "#eff6ff"),
		(report.summary.open, _("Open"), "#f5f3ff"),
		(report.summary.overdue, _("Overdue"), "#fef2f2" if report.summary.overdue else "#f9fafb"),
		(report.summary.waiting, _("Waiting on you"), "#fffbeb" if report.summary.waiting else "#f9fafb"),
		(f"{report.summary.completion_pct:.0f}%", _("Complete"), "#ecfdf5"),
		(report.summary.hours, _("Hours"), "#ecfeff"),
	]
	# REPORT_TEMPLATE is a module constant; no user input is ever used as template source.
	return frappe.render_template(  # nosemgrep: frappe-ssti
		REPORT_TEMPLATE,
		{
			"r": report,
			"note": (note or "").strip(),
			"colour": LEVEL_COLOUR.get(status.level if status else "none", LEVEL_COLOUR["none"]),
			"tiles": tiles,
			"risk_releases": [rel for rel in report.releases if rel["risk"] in ("late", "risk")],
		},
	)


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


def default_subject(report: frappe._dict) -> str:
	"""Default email subject."""
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
) -> str:
	"""Email the report and log it as a Project Status Report. Returns the log document name."""
	if not has_capability(project, "can_manage_releases"):
		frappe.throw(_("You are not allowed to send status reports for Project {0}").format(project))
	addresses = parse_recipients(recipients)
	# Frappe only notices a missing outgoing account when the queue sends; tell the user now instead of "sending" nothing.
	EmailAccount.find_outgoing(_raise_error=True)
	report = build_report(project, from_date, to_date)
	html = render_html(report, note)
	subject = (subject or default_subject(report))[:140]
	frappe.sendmail(
		recipients=addresses,
		subject=subject,
		message=html,
		reference_doctype="Project",
		reference_name=project,
		add_unsubscribe_link=0,
	)
	log = frappe.get_doc(
		{
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
			"body": html,
		}
	)
	log.insert(ignore_permissions=True)
	return log.name


def get_pdf_bytes(project: str, from_date, to_date, note: str | None = None) -> bytes:
	"""PDF of the report (wkhtmltopdf through Frappe)."""
	from frappe.utils.pdf import get_pdf

	return get_pdf(render_html(build_report(project, from_date, to_date), note))


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
			filters={**filters, "tracker_report_recipients": ["is", "set"]},
			fields=["name", "tracker_report_recipients"],
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
					project.name, from_date, to_date, project.tracker_report_recipients, scheduled=True
				)
			except Exception:
				frappe.log_error(title=f"Auri PMS: scheduled status report failed for {project.name}")
