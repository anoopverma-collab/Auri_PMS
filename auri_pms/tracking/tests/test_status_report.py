"""Client status report: data, HTML, emailing, PDF and the weekly schedule."""

import frappe
from frappe.utils import add_days, getdate, today

from auri_pms.tracking import api
from auri_pms.tracking.status_report import (
	build_report,
	get_pdf_bytes,
	parse_recipients,
	render_html,
	send_report,
	send_scheduled_reports,
)
from auri_pms.tracking.tests.utils import DEV, MGR, OUT, TM, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestStatusReport(TrackerTestCase):
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
