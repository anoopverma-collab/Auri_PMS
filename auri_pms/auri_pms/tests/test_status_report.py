"""Client status report: data, HTML, emailing, PDF and the weekly schedule."""

import frappe
from frappe.utils import add_days, getdate, today

from auri_pms.auri_pms import api
from auri_pms.auri_pms.status_report import (
	build_report,
	default_subject,
	get_pdf_bytes,
	parse_recipients,
	render_html,
	send_report,
	send_scheduled_reports,
)
from auri_pms.auri_pms.tests.utils import DEV, MGR, OUT, TM, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestStatusReport(TrackerTestCase):
	def setUp(self):
		super().setUp()
		self.snapshot_settings()
		# the tests describe the built-in layout; a site default template must not change what they render
		frappe.db.set_single_value("PMS Settings", "report_email_template", "")
		frappe.clear_cache(doctype="PMS Settings")

	def snapshot_settings(self):
		"""Put every PMS Settings value and the Section Order rows back when the test ends.

		The tests run on a real site and some of them commit, so whatever a person saved in PMS Settings
		must survive a test run."""
		doc = frappe.get_doc("PMS Settings")
		fields = {
			df.fieldname: doc.get(df.fieldname)
			for df in doc.meta.fields
			if df.fieldtype not in ("Section Break", "Column Break", "Tab Break", "Table")
		}
		rows = [r.section for r in doc.get("report_section_order") or []]

		def restore():
			for fieldname, value in fields.items():
				frappe.db.set_single_value("PMS Settings", fieldname, value)
			frappe.db.delete("PMS Report Section", {"parent": "PMS Settings"})
			for idx, section in enumerate(rows, 1):
				frappe.get_doc(
					{
						"doctype": "PMS Report Section",
						"parent": "PMS Settings",
						"parenttype": "PMS Settings",
						"parentfield": "report_section_order",
						"idx": idx,
						"section": section,
					}
				).db_insert()
			frappe.clear_cache(doctype="PMS Settings")

		self.addCleanup(restore)

	def report(self, start=-7, end=0, project=None):
		return build_report(project or self.ALP, days(start), days(end))

	def closed_item(self, **kw):
		item = self.new_item(MGR, tracker="Task", **kw)
		self.save_as(MGR, item, status="Closed")
		return item

	def emails_to(self, address):
		parents = frappe.get_all("Email Queue Recipient", filters={"recipient": address}, pluck="parent")
		return frappe.get_all(
			"Email Queue", filters={"name": ["in", parents or [""]]}, fields=["name", "message"]
		)

	def test_sections(self):
		"""Delivered, in progress, coming up, overdue and blocked tickets land in the right sections."""
		done = self.closed_item(subject="Shipped login")
		started = self.new_item(MGR, tracker="Task", subject="Building search", due_date=days(5))
		self.save_as(MGR, started, status="In Progress")
		late = self.new_item(MGR, tracker="Task", subject="Late thing", due_date=days(-4))
		soon = self.new_item(MGR, tracker="Task", subject="Starts soon", due_date=days(6))
		blocked = self.new_item(MGR, tracker="Task", subject="Waiting")
		blocked.append("relations", {"relation_type": "Blocked by", "related_work_item": soon.name})
		self.save_as(MGR, blocked)
		report = self.report()
		self.assertEqual([i.name for i in report.delivered], [done.name])
		self.assertEqual([i.name for i in report.in_progress], [started.name])
		self.assertIn(soon.name, [i.name for i in report.next_up])
		self.assertEqual([i["name"] for i in report.overdue], [late.name])
		self.assertEqual(report.overdue[0]["days"], 4)
		self.assertEqual([b["name"] for b in report.blocked], [blocked.name])
		self.assertEqual((report.summary.delivered, report.summary.open, report.summary.overdue), (1, 4, 1))

	def test_period_limits_delivered(self):
		"""Only tickets closed inside the period count as delivered."""
		old = self.closed_item()
		frappe.db.set_value(
			"Work Item", old.name, "closed_on", f"{days(-30)} 10:00:00", update_modified=False
		)
		self.closed_item()
		self.assertEqual(self.report(-7, 0).summary.delivered, 1)
		self.assertEqual(self.report(-40, 0).summary.delivered, 2)

	def test_hours_in_period(self):
		"""Hours, billable split and activity breakdown cover only the period."""
		item = self.new_item(MGR, tracker="Task")
		self.logged_time(DEV, item.name, 5, date=days(-2))
		self.logged_time(DEV, item.name, 2, date=days(-1), is_billable=0, activity="Meeting")
		self.logged_time(DEV, item.name, 4, date=days(-20))
		report = self.report()
		self.assertEqual(
			(report.summary.hours, report.summary.billable, report.summary.non_billable), (7, 5, 2)
		)
		self.assertEqual(
			{a["label"]: a["billable"] + a["non_billable"] for a in report.activities},
			{"Development": 5, "Meeting": 2},
		)

	def test_range_validation_and_access(self):
		"""Bad ranges are rejected and outsiders cannot report on a private project."""
		self.assertThrows("To date cannot be before From date", lambda: self.report(0, -1))
		self.assertThrows("at most 366 days", lambda: build_report(self.ALP, days(-400), days(0)))
		with self.as_user(OUT):
			self.assertRaises(frappe.PermissionError, build_report, self.ALP, days(-7), days(0))

	def test_html_has_the_facts_and_escapes_input(self):
		"""The HTML names the project, status and tickets; user text cannot inject markup."""
		self.closed_item(subject='Fix a < b & "quotes"')
		html = render_html(self.report(), note="Hello <b>team</b>\nSecond line")
		self.assertIn("Project Alpha", html)
		self.assertIn("ALP", html)
		self.assertIn("Fix a &lt; b &amp; &#34;quotes&#34;", html)
		self.assertNotIn("<b>team</b>", html)
		self.assertIn("Hello &lt;b&gt;team&lt;/b&gt;<br>Second line", html)
		self.assertIn("Delivered in this period", html)

	def test_recipient_parsing(self):
		"""Recipients are split, validated and de-duplicated."""
		self.assertEqual(
			parse_recipients("a@x.com, B@x.com;a@x.com\nc@x.com"), ["a@x.com", "b@x.com", "c@x.com"]
		)
		self.assertThrows("not a valid email", lambda: parse_recipients("nope"))
		self.assertThrows("at least one recipient", lambda: parse_recipients("  "))
		self.assertThrows("At most 20", lambda: parse_recipients([f"u{n}@x.com" for n in range(21)]))

	def test_send_logs_and_queues_email(self):
		"""Sending queues one email and keeps a log with the exact HTML."""
		self.closed_item(subject="Delivered thing")
		with self.as_user(MGR):
			name = send_report(
				self.ALP, days(-7), days(0), "client@example.com", "Weekly update", "Thanks all"
			)
		log = frappe.get_doc("Project Status Report", name)
		self.assertEqual(
			(log.project, log.sent_to, log.subject, log.scheduled),
			(self.ALP, "client@example.com", "Weekly update", 0),
		)
		self.assertIn("Delivered thing", log.body)
		self.assertIn("Thanks all", log.body)
		self.assertTrue(self.emails_to("client@example.com"))

	def test_cc_and_bcc_are_sent_and_logged(self):
		"""CC and BCC addresses get the email too; an address already in To is not repeated; the log keeps all three lists."""
		with self.as_user(MGR):
			name = send_report(
				self.ALP,
				days(-7),
				days(0),
				"client@example.com",
				cc="boss@example.com, client@example.com",
				bcc="audit@example.com",
			)
		log = frappe.get_doc("Project Status Report", name)
		self.assertEqual(
			(log.sent_to, log.sent_cc, log.sent_bcc),
			("client@example.com", "boss@example.com", "audit@example.com"),
		)
		self.assertEqual(log.recipient_count, 3)
		for address in ("client@example.com", "boss@example.com", "audit@example.com"):
			self.assertTrue(self.emails_to(address), address)

	def test_cc_must_be_valid_addresses(self):
		with self.as_user(MGR):
			self.assertThrows(
				"not a valid email address",
				lambda: send_report(self.ALP, days(-7), days(0), "client@example.com", cc="nonsense"),
			)

	def test_delivery_status_is_tracked(self):
		"""The log counts the emails triggered and follows their Email Queue state."""
		with self.as_user(MGR):
			name = send_report(self.ALP, days(-7), days(0), "a@example.com, b@example.com")
		log = frappe.get_doc("Project Status Report", name)
		self.assertEqual((log.recipient_count, log.delivery_status, log.sent_count), (2, "Queued", 0))
		frappe.db.set_value(
			"Email Queue Recipient",
			{
				"parenttype": "Email Queue",
				"recipient": "a@example.com",
				"parent": ["in", self.queues_of(name)],
			},
			"status",
			"Sent",
		)
		log.refresh_delivery_status()
		self.assertEqual((log.delivery_status, log.sent_count, log.failed_count), ("Partially Sent", 1, 0))
		frappe.db.set_value(
			"Email Queue Recipient",
			{
				"parenttype": "Email Queue",
				"recipient": "b@example.com",
				"parent": ["in", self.queues_of(name)],
			},
			"status",
			"Error",
		)
		log.refresh_delivery_status()
		self.assertEqual((log.delivery_status, log.sent_count, log.failed_count), ("Partially Sent", 1, 1))

	def keep_settings(self, *fieldnames):
		"""Restore these PMS Settings values (and the cache) when the test ends, whatever it saved."""
		original = {f: frappe.db.get_single_value("PMS Settings", f) for f in fieldnames}

		def restore():
			for fieldname, value in original.items():
				frappe.db.set_single_value("PMS Settings", fieldname, value)
			frappe.clear_cache(doctype="PMS Settings")

		self.addCleanup(restore)

	def test_settings_control_sections_limits_and_template(self):
		"""PMS Settings hide sections and can swap in an Email Template."""
		self.closed_item(subject="Delivered thing")
		self.closed_item(subject="Another delivered")
		self.keep_settings("show_report_time", "report_email_template")
		settings = frappe.get_doc("PMS Settings")
		settings.show_report_time = 0
		settings.save()
		report = build_report(self.ALP, days(-7), days(0))
		html = render_html(report)
		self.assertNotIn("Time spent in this period", html)
		self.assertIn("Delivered in this period", html)
		# every ticket is listed, never cut off
		self.assertEqual((len(report.delivered), report.delivered_more), (2, 0))
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": "Test PMS Report",
				"subject": "Custom {{ r.project.project_name }}",
				"response": "<p>Custom body {{ r.summary.delivered }}</p>",
				"auri_pms_enabled": 1,
			}
		).insert()
		settings.report_email_template = template.name
		settings.save()
		self.assertEqual(render_html(report).strip(), "<p>Custom body 2</p>")
		self.assertTrue(default_subject(report).startswith("Custom "))

	def test_tickets_can_be_hidden_or_removed_from_a_report(self):
		"""A flagged ticket never appears; an excluded one is left out of that report only."""
		hidden = self.closed_item(subject="Internal only")
		removed = self.closed_item(subject="Removed this time")
		kept = self.closed_item(subject="Stays in")
		frappe.db.set_value("Work Item", hidden.name, "hide_from_client_report", 1)
		report = build_report(self.ALP, days(-7), days(0))
		self.assertEqual(sorted(t["name"] for t in report.tickets), sorted([removed.name, kept.name]))
		report = build_report(self.ALP, days(-7), days(0), exclude=[removed.name])
		self.assertEqual([t["name"] for t in report.tickets], [kept.name])
		self.assertEqual(report.summary.delivered, 1)
		html = render_html(report)
		self.assertNotIn("Internal only", html)
		self.assertNotIn("Removed this time", html)
		self.assertIn("Stays in", html)
		self.assertIn(removed.name, [t["name"] for t in build_report(self.ALP, days(-7), days(0)).tickets])

	def test_hidden_tickets_do_not_count_in_the_client_health(self):
		"""An overdue ticket flagged as hidden does not turn the client's status red."""
		from auri_pms.auri_pms.health import get_health

		item = self.new_item(MGR, tracker="Task", due_date=days(-5))
		frappe.db.set_value("Work Item", item.name, "hide_from_client_report", 1)
		self.assertEqual(get_health(self.ALP).flow.total, 1)
		self.assertEqual(get_health(self.ALP, client_view=True).flow.total, 0)

	def test_ready_made_email_templates_render(self):
		"""The shipped Email Templates render with the report data and respect the section switches."""
		from auri_pms.install import EMAIL_TEMPLATES, ensure_email_templates

		ensure_email_templates()
		self.keep_settings("report_email_template", "show_report_delivered")
		self.closed_item(subject="Shipped feature")
		settings = frappe.get_doc("PMS Settings")
		for name, *_rest in EMAIL_TEMPLATES:
			settings.report_email_template = name
			settings.save()
			report = build_report(self.ALP, days(-7), days(0))
			html = render_html(report, "Hi there")
			self.assertIn("Shipped feature", html, name)
			self.assertIn("Hi there", html, name)
			self.assertIn("Project Alpha", default_subject(report), name)
		# a template chosen for one send overrides the settings default
		html = render_html(build_report(self.ALP, days(-7), days(0)), template="PMS Status Report - Summary")
		self.assertIn("Shipped feature", html)
		# the built-in layout can be forced even though a default template is chosen
		report = build_report(self.ALP, days(-7), days(0))
		self.assertIn("Project status report", render_html(report, template="__builtin__"))
		self.assertNotEqual(render_html(report, template="__builtin__"), render_html(report))
		settings.show_report_delivered = 0
		settings.save()
		self.assertNotIn("Shipped feature", render_html(build_report(self.ALP, days(-7), days(0))))

	def test_sections_and_added_tickets_apply_to_one_report(self):
		"""Section switches and added tickets change a single render, not the settings."""
		hidden = self.closed_item(subject="Hidden but added")
		self.closed_item(subject="Normal delivered")
		frappe.db.set_value("Work Item", hidden.name, "hide_from_client_report", 1)
		report = build_report(self.ALP, days(-7), days(0), include=[hidden.name])
		self.assertEqual([i.name for i in report.extra], [hidden.name])
		from auri_pms.auri_pms.status_report import section_switches, visible_tickets

		listed = lambda **off: [  # noqa: E731
			t["name"] for t in visible_tickets(report.tickets, section_switches(off))
		]
		self.assertTrue(listed())
		self.assertEqual(listed(delivered=0), [])
		html = render_html(report, sections={"delivered": 0}, template="__builtin__")
		# switching a section off removes its figure from the summary tiles and sentence too
		from auri_pms.install import ensure_email_templates

		ensure_email_templates()
		corp = "PMS Status Report - Corporate"  # the layout with a summary sentence
		on = render_html(report, template=corp)
		off = render_html(report, sections={"delivered": 0, "time": 0}, template=corp)
		self.assertIn("tickets were delivered", on)
		self.assertNotIn("tickets were delivered", off)
		self.assertIn("tickets were raised", on)
		self.assertIn("Overall completion", on)
		quiet = render_html(report, sections={"created": 0, "completion": 0}, template=corp)
		self.assertNotIn("tickets were raised", quiet)
		self.assertNotIn("Overall completion", quiet)
		tiles_on = render_html(report, template="__builtin__")
		tiles_off = render_html(
			report, sections={"delivered": 0, "created": 0, "completion": 0}, template="__builtin__"
		)
		self.assertIn(">Delivered<", tiles_on)
		for label in ("Delivered", "New tickets", "Complete"):
			self.assertNotIn(f">{label}<", tiles_off)
		self.assertNotIn(">Delivered<", off)
		self.assertIn("Additional tickets", html)
		self.assertIn("Hidden but added", html)
		self.assertNotIn("Delivered in this period", html)
		self.assertIn("Delivered in this period", render_html(report))
		noted = build_report(self.ALP, days(-7), days(0), include={hidden.name: "Please review <b>this</b>"})
		self.assertEqual(noted.extra[0].report_note, "Please review <b>this</b>")
		for template in (None, "PMS Status Report - Summary", "PMS Status Report - Summary Dark"):
			html = render_html(noted, template=template)
			self.assertIn("Please review &lt;b&gt;this&lt;/b&gt;", html, template)
		# the Additional tickets section has its own switch
		for template in ("__builtin__", "PMS Status Report - Corporate", "PMS Status Report - Summary"):
			self.assertIn("Additional tickets", render_html(noted, template=template), template)
			self.assertNotIn(
				"Additional tickets", render_html(noted, sections={"extra": 0}, template=template), template
			)
		self.assertEqual(build_report(self.ALP, days(-7), days(0), [hidden.name], [hidden.name]).extra, [])
		for name in ("PMS Status Report - Summary", "PMS Status Report - Summary Dark"):
			self.assertIn("Hidden but added", render_html(report, template=name))

	def test_only_enabled_email_templates_can_be_used(self):
		"""A template that is not enabled for Auri PMS is refused, so it cannot be picked by accident."""
		frappe.get_doc(
			{"doctype": "Email Template", "name": "Not for PMS", "subject": "x", "response": "<p>x</p>"}
		).insert()
		report = build_report(self.ALP, days(-7), days(0))
		self.assertRaises(frappe.ValidationError, render_html, report, None, "Not for PMS")

	def test_status_reasons_follow_the_sections(self):
		"""Reasons of a switched-off section leave the banner, and the level and score are worked out again."""
		from auri_pms.auri_pms.health import status_for_sections

		status = {
			"level": "red",
			"label": "Off Track",
			"score": 65,
			"reasons": [
				{"level": "red", "text": "late", "section": "issues"},
				{"level": "amber", "text": "hours", "section": "time"},
				{"level": "info", "text": "waiting", "section": "waiting"},
			],
		}
		same = status_for_sections(status, {"issues": 1, "time": 1, "waiting": 1})
		self.assertEqual((same["level"], len(same["reasons"])), ("red", 3))
		no_issues = status_for_sections(status, {"issues": 0, "time": 1, "waiting": 1})
		self.assertEqual(
			(no_issues["level"], no_issues["label"], no_issues["score"]), ("amber", "At Risk", 90)
		)
		clear = status_for_sections(status, {"issues": 0, "time": 0, "waiting": 0})
		self.assertEqual((clear["level"], clear["score"]), ("green", 100))
		self.assertEqual([r["level"] for r in clear["reasons"]], ["green"])

	def test_section_order_can_be_set_per_report_and_in_settings(self):
		"""A report lists its sections in the order chosen for it, else the PMS Settings order, else its own."""
		from auri_pms.auri_pms.status_report import (
			clean_order,
			configured_order,
			current_order,
			layout_order,
			visible_tickets,
		)
		from auri_pms.install import ensure_email_templates

		ensure_email_templates()
		corp = "PMS Status Report - Corporate"
		report = build_report(self.ALP, days(-7), days(0))
		first = lambda html, a, b: html.index(a) < html.index(b)  # noqa: E731
		delivered, in_progress = "Delivered in this period", ">In progress"
		# the layout's own order
		self.assertTrue(first(render_html(report, template=corp), delivered, in_progress))
		# chosen for one report
		html = render_html(report, template=corp, order=["in_progress", "delivered"])
		self.assertTrue(first(html, in_progress, delivered))
		self.assertEqual(current_order(corp, ["in_progress", "delivered"])[:2], ["in_progress", "delivered"])
		# saved in PMS Settings; an unknown or repeated key is ignored and the rest are added at the end
		self.keep_section_order()
		settings = frappe.get_doc("PMS Settings")
		settings.set("report_section_order", [{"section": "In progress"}, {"section": "Delivered"}])
		settings.save()
		self.assertEqual(configured_order()[:2], ["in_progress", "delivered"])
		self.assertEqual(len(configured_order()), 10)
		self.assertTrue(first(render_html(report, template=corp), in_progress, delivered))
		self.assertTrue(
			first(render_html(report, template=corp, order=["delivered"]), delivered, in_progress)
		)
		self.assertEqual(clean_order(["time", "nope", "time"])[:2], ["time", "modules"])
		self.assertEqual(layout_order('{% set default_order = ["plan", "risks"] %}')[:2], ["plan", "risks"])
		# the ticket list of the page follows the order of the sections
		tickets = [
			{"name": "A-1", "subject": "a", "section": "x", "key": "delivered"},
			{"name": "A-2", "subject": "b", "section": "y", "key": "waiting"},
		]
		self.assertEqual(
			[
				t["name"]
				for t in visible_tickets(tickets, {"delivered": 1, "waiting": 1}, ["waiting", "delivered"])
			],
			["A-2", "A-1"],
		)

	def test_default_recipients_and_subject(self):
		"""Settings add default recipients to each project's own, and give a default subject."""
		from auri_pms.auri_pms.api import get_status_report_html
		from auri_pms.auri_pms.status_report import default_subject, merge_recipients

		self.assertEqual(
			merge_recipients("a@x.com, b@x.com", "B@x.com; c@x.com"), "a@x.com, b@x.com, c@x.com"
		)
		self.keep_settings("report_default_recipients", "report_default_subject", "report_email_template")
		settings = frappe.get_doc("PMS Settings")
		settings.report_default_recipients = "team@example.com"
		settings.report_default_subject = "{project} update {from_date}"
		settings.save()
		report = build_report(self.ALP, days(-7), days(0))
		self.assertTrue(default_subject(report).startswith("Project Alpha update "))
		frappe.db.set_value("Project", self.ALP, "tracker_report_recipients", "client@example.com")
		with self.as_user(MGR):
			preview = get_status_report_html(self.ALP, days(-7), days(0))
		self.assertEqual(preview["recipients"], "client@example.com, team@example.com")
		settings.report_default_recipients = "not-an-address"
		self.assertRaises(frappe.ValidationError, settings.save)

	def test_report_too_large_to_email_is_refused(self):
		"""A report over the size limit is refused up front with a clear message and nothing is queued."""
		from unittest.mock import patch

		with patch("auri_pms.auri_pms.status_report.MAX_EMAIL_BYTES", 100), self.as_user(MGR):
			self.assertThrows(
				"too large to email",
				lambda: send_report(self.ALP, days(-7), days(0), "client@example.com"),
			)
		self.assertFalse(self.emails_to("client@example.com"))

	def keep_section_order(self):
		"""Put the Section Order rows of PMS Settings back when the test ends (the tests run on a real site)."""
		original = [r.section for r in frappe.get_doc("PMS Settings").get("report_section_order") or []]

		def restore():
			settings = frappe.get_doc("PMS Settings")
			settings.set("report_section_order", [{"section": section} for section in original])
			settings.save()
			frappe.clear_cache(doctype="PMS Settings")

		self.addCleanup(restore)

	def queues_of(self, log_name):
		return frappe.get_all(
			"Email Queue",
			filters={"reference_doctype": "Project Status Report", "reference_name": log_name},
			pluck="name",
		)

	def test_only_report_managers_can_send(self):
		"""A developer cannot send client reports; a project manager can."""
		with self.as_user(DEV):
			self.assertThrows(
				"not allowed to send status reports",
				lambda: send_report(self.ALP, days(-7), days(0), "client@example.com"),
			)
		with self.as_user(MGR):
			self.assertTrue(send_report(self.ALP, days(-7), days(0), "client@example.com"))

	def test_missing_mail_account_is_reported_and_nothing_is_logged(self):
		"""Without an outgoing Email Account the user gets Frappe's error up front and no log is written."""
		from unittest.mock import patch

		from frappe.email.doctype.email_account.email_account import EmailAccount

		before = frappe.db.count("Project Status Report")
		error = frappe.OutgoingEmailError(
			"Please setup default outgoing Email Account from Tools > Email Account"
		)
		with self.as_user(MGR), patch.object(EmailAccount, "find_outgoing", side_effect=error):
			self.assertRaises(
				frappe.OutgoingEmailError, send_report, self.ALP, days(-7), days(0), "client@example.com"
			)
		self.assertEqual(frappe.db.count("Project Status Report"), before)

	def test_preview_api(self):
		"""The preview API returns HTML, a subject, the stored recipients and whether the user may send."""
		frappe.db.set_value("Project", self.ALP, "tracker_report_recipients", "client@example.com")
		with self.as_user(MGR):
			data = api.get_status_report_html(self.ALP, days(-7), days(0), "Note")
		self.assertIn("Project Alpha", data["html"])
		self.assertTrue(data["can_send"])
		self.assertEqual(data["recipients"], "client@example.com")
		with self.as_user(DEV):
			self.assertFalse(api.get_status_report_html(self.ALP, days(-7), days(0))["can_send"])

	def test_pdf(self):
		"""The report can be rendered to a PDF."""
		self.assertTrue(get_pdf_bytes(self.ALP, days(-7), days(0)).startswith(b"%PDF"))

	def test_history_is_visible_to_members_only(self):
		"""Sent reports are listed for the project; outsiders do not see them."""
		with self.as_user(MGR):
			name = send_report(self.ALP, days(-7), days(0), "client@example.com")
			self.assertIn(name, [r.name for r in api.get_status_report_history(self.ALP)])
		with self.as_user(OUT):
			self.assertEqual(api.get_status_report_history(self.ALP), [])

	def test_weekly_schedule(self):
		"""A project with recipients and today's weekday gets one scheduled report per day."""
		weekday = getdate(today()).strftime("%A")
		frappe.db.set_value(
			"Project",
			self.ALP,
			{"tracker_report_recipients": "client@example.com", "tracker_report_weekday": weekday},
		)
		with self.as_user(TM):
			pass
		send_scheduled_reports()
		send_scheduled_reports()  # second run the same day: no duplicate
		logs = frappe.get_all(
			"Project Status Report", {"project": self.ALP, "scheduled": 1}, ["from_date", "to_date"]
		)
		self.assertEqual(len(logs), 1)
		self.assertEqual((str(logs[0].from_date), str(logs[0].to_date)), (days(-7), days(-1)))

	def test_monthly_schedule(self):
		"""A monthly project is sent on its day of the month for the previous calendar month, once."""
		today_ = getdate(today())
		frappe.db.set_value(
			"Project",
			self.ALP,
			{
				"tracker_report_recipients": "client@example.com",
				"tracker_report_month_day": str(today_.day),
				"tracker_report_weekday": "",
			},
		)
		send_scheduled_reports()
		send_scheduled_reports()
		logs = frappe.get_all(
			"Project Status Report", {"project": self.ALP, "scheduled": 1}, ["from_date", "to_date"]
		)
		self.assertEqual(len(logs), 1)
		last_end = add_days(today_.replace(day=1), -1)
		self.assertEqual((logs[0].from_date, logs[0].to_date), (last_end.replace(day=1), last_end))

	def test_weekly_and_monthly_together(self):
		"""Both schedules can be set on one project; on a day that matches both, both reports go out once."""
		today_ = getdate(today())
		frappe.db.set_value(
			"Project",
			self.ALP,
			{
				"tracker_report_recipients": "client@example.com",
				"tracker_report_weekday": today_.strftime("%A"),
				"tracker_report_month_day": str(today_.day),
			},
		)
		send_scheduled_reports()
		send_scheduled_reports()
		self.assertEqual(frappe.db.count("Project Status Report", {"project": self.ALP, "scheduled": 1}), 2)

	def test_monthly_schedule_skips_other_days(self):
		"""Nothing is sent when today is not the chosen day of the month."""
		today_ = getdate(today())
		other = str(today_.day % 28 + 1)
		frappe.db.set_value(
			"Project",
			self.ALP,
			{
				"tracker_report_recipients": "client@example.com",
				"tracker_report_month_day": other,
			},
		)
		send_scheduled_reports()
		self.assertFalse(frappe.db.count("Project Status Report", {"scheduled": 1, "project": self.ALP}))

	def test_schedule_skips_other_weekdays_and_missing_recipients(self):
		"""Nothing is sent on other weekdays or without recipients."""
		today_ = getdate(today())
		other = add_days(today_, 1).strftime("%A")
		frappe.db.set_value(
			"Project",
			self.ALP,
			{"tracker_report_recipients": "client@example.com", "tracker_report_weekday": other},
		)
		frappe.db.set_value(
			"Project",
			self.BET,
			{"tracker_report_recipients": "", "tracker_report_weekday": today_.strftime("%A")},
		)
		send_scheduled_reports()
		self.assertFalse(
			frappe.db.count(
				"Project Status Report", {"scheduled": 1, "project": ["in", [self.ALP, self.BET]]}
			)
		)
