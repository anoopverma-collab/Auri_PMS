"""Email intake (T-120 .. T-123)."""

import frappe

from auri_pms.auri_pms.tests.utils import DEV, MGR, TrackerTestCase


class TestEmailIntake(TrackerTestCase):
	def account(self, name, project=None, tracker=None):
		return frappe.get_doc(
			{
				"doctype": "Email Account",
				"email_account_name": name,
				"email_id": f"{name.lower().replace(' ', '.')}@example.com",
				"enable_incoming": 1,
				"awaiting_password": 0,
				"password": "not-used",
				"imap_folder": [{"folder_name": "INBOX", "append_to": "Communication"}],
				"tracker_project": project,
				"tracker_default_tracker": tracker,
			}
		).insert(ignore_permissions=True)

	def receive(self, account, sender, subject, body="<p>Please help</p>"):
		return frappe.get_doc(
			{
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": "Email",
				"sent_or_received": "Received",
				"email_account": account.name,
				"sender": sender,
				"recipients": account.email_id,
				"subject": subject,
				"content": body,
			}
		).insert(ignore_permissions=True)

	def test_t120_known_sender_creates_item(self):
		"""T-120: a received email creates a Work Item authored by the matching user and links the Communication."""
		account = self.account("Support A", self.ALP, "Support")
		comm = self.receive(account, DEV, "Printer broken")
		item = frappe.get_doc("Work Item", frappe.db.get_value("Communication", comm.name, "reference_name"))
		self.assertEqual(
			(item.project, item.author, item.raised_by_email, item.subject),
			(self.ALP, DEV, DEV, "Printer broken"),
		)
		self.assertEqual(frappe.db.get_value("Communication", comm.name, "reference_doctype"), "Work Item")
		self.assertIn("Please help", item.description)

	def test_t121_unknown_sender_is_administrator(self):
		"""T-121: an unknown sender gives an item authored by Administrator."""
		account = self.account("Support B", self.ALP, "Support")
		comm = self.receive(account, "stranger@example.org", "Hello")
		item = frappe.get_doc("Work Item", frappe.db.get_value("Communication", comm.name, "reference_name"))
		self.assertEqual((item.author, item.raised_by_email), ("Administrator", "stranger@example.org"))

	def test_t122_reply_links_to_existing_item(self):
		"""T-122: a reply with [ALP-00001] in the subject links to that item and creates no new one."""
		item = self.new_item(MGR)
		account = self.account("Support C", self.ALP, "Support")
		before = frappe.db.count("Work Item")
		comm = self.receive(account, DEV, f"Re: [{item.name}] Printer broken")
		self.assertEqual(frappe.db.count("Work Item"), before)
		self.assertEqual(frappe.db.get_value("Communication", comm.name, "reference_name"), item.name)

	def test_t123_unmapped_account_does_nothing(self):
		"""T-123: an account without tracker_project creates no item."""
		account = self.account("Support D")
		before = frappe.db.count("Work Item")
		comm = self.receive(account, DEV, "Nothing should happen")
		self.assertEqual(frappe.db.count("Work Item"), before)
		self.assertFalse(frappe.db.get_value("Communication", comm.name, "reference_name"))
