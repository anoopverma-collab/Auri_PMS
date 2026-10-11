"""Risk Register: scoring, rules, visibility and how risks feed the dashboards and the client report."""

import frappe
from frappe.utils import add_days, today

from auri_pms.tracking import api
from auri_pms.tracking.risk import client_risks, my_risks, risk_summary
from auri_pms.tracking.status_report import build_report, render_html
from auri_pms.tracking.tests.utils import DEV, MGR, OUT, REP, TM, TrackerTestCase

CRITICAL = {"probability": "5 - Almost Certain", "impact": "3 - Moderate"}  # 15
HIGH = {"probability": "4 - Likely", "impact": "3 - Moderate"}  # 12
LOW = {"probability": "2 - Unlikely", "impact": "2 - Minor"}  # 4


class TestRiskRegister(TrackerTestCase):
	def risk(self, user=MGR, project=None, **kw):
		values = {
			"doctype": "Risk Register",
			"project": project or self.ALP,
			"title": kw.pop("title", "A risk"),
			**kw,
		}
		with self.as_user(user):
			return frappe.get_doc(values).insert()

	# ------------------------------------------------------------------ the document
	def test_score_and_level_follow_probability_and_impact(self):
		for values, score, level in (
			(CRITICAL, 15, "Critical"),
			(HIGH, 12, "High"),
			({"probability": "3 - Possible", "impact": "3 - Moderate"}, 9, "Medium"),
			(LOW, 4, "Low"),
			({"probability": "5 - Almost Certain", "impact": "5 - Severe"}, 25, "Critical"),
		):
			doc = self.risk(**values)
			self.assertEqual((doc.risk_score, doc.risk_level), (score, level), values)

	def test_name_carries_the_project_identifier_and_numbers_each_project_on_its_own(self):
		first, second = self.risk(), self.risk()
		other = self.risk(project=self.BET)
		self.assertTrue(first.name.startswith("ALP-RISK-"))
		self.assertEqual(int(second.name.rsplit("-", 1)[1]), int(first.name.rsplit("-", 1)[1]) + 1)
		self.assertEqual(other.name, "BET-RISK-0001")

	def test_members_who_can_create_items_raise_risks_but_outsiders_cannot(self):
		self.assertTrue(self.risk(REP).name)
		self.assertThrows("not allowed to manage risks", lambda: self.risk(OUT))

	def test_only_managers_delete_risks(self):
		doc = self.risk(DEV)
		with self.as_user(DEV):
			self.assertThrows(
				"not allowed to delete risks", lambda: frappe.delete_doc("Risk Register", doc.name)
			)
		with self.as_user(MGR):
			frappe.delete_doc("Risk Register", doc.name)
		self.assertFalse(frappe.db.exists("Risk Register", doc.name))

	def test_closed_on_is_stamped_and_cleared(self):
		doc = self.risk()
		self.assertIsNone(doc.closed_on)
		doc = self.save_as(MGR, doc, status="Closed")
		self.assertEqual(str(doc.closed_on), today())
		doc = self.save_as(MGR, doc, status="Monitoring")
		self.assertIsNone(doc.closed_on)

	def test_related_work_item_must_be_in_the_same_project(self):
		other = self.new_item(MGR, project=self.BET, tracker="Task")
		self.assertThrows("does not belong to Project", lambda: self.risk(related_work_item=other.name))
		same = self.new_item(MGR, tracker="Task")
		self.assertEqual(self.risk(related_work_item=same.name).related_work_item, same.name)

	def test_mitigation_cannot_be_due_before_the_risk_was_identified(self):
		self.assertThrows(
			"cannot be before",
			lambda: self.risk(identified_on=today(), mitigation_due=add_days(today(), -3)),
		)

	def test_outsiders_do_not_see_the_risks_of_a_private_project(self):
		self.risk()
		with self.as_user(OUT):
			self.assertEqual(frappe.get_list("Risk Register", filters={"project": self.ALP}), [])
		with self.as_user(DEV):
			self.assertTrue(frappe.get_list("Risk Register", filters={"project": self.ALP}))

	# ------------------------------------------------------------------ dashboards
	def test_summary_counts_levels_matrix_and_overdue(self):
		self.risk(
			title="Top",
			**CRITICAL,
			mitigation_due=add_days(today(), -2),
			identified_on=add_days(today(), -10),
		)
		self.risk(title="Mid", **HIGH, status="Mitigating")
		self.risk(title="Done", **LOW, status="Closed")
		self.risk(title="Happened", **HIGH, status="Occurred")
		with self.as_user(MGR):
			data = risk_summary(self.ALP)
		self.assertEqual((data.total, data.open, data.overdue, data.occurred, data.closed), (4, 2, 1, 1, 1))
		self.assertEqual(data.by_level, {"Critical": 1, "High": 1, "Medium": 0, "Low": 0})
		self.assertEqual(data.matrix[0][2], 1)  # probability 5, impact 3
		self.assertEqual(data.matrix[1][2], 1)  # probability 4, impact 3
		self.assertEqual([r["title"] for r in data.top], ["Top", "Mid"])
		self.assertTrue(data.top[0]["overdue"])

	def test_critical_and_overdue_risks_lower_the_project_status(self):
		self.new_item(MGR, tracker="Task")
		before = api.get_project_health(self.ALP, "3m")
		self.assertFalse([r for r in before.status.reasons if r["level"] != "green"])
		self.risk(**CRITICAL, mitigation_due=add_days(today(), -1), identified_on=add_days(today(), -5))
		with self.as_user(MGR):
			after = api.get_project_health(self.ALP, "3m")
		texts = [r["text"] for r in after.status.reasons]
		self.assertTrue(any("critical risk is open" in t for t in texts), texts)
		self.assertTrue(any("past the mitigation date" in t for t in texts), texts)
		self.assertEqual(after.status.level, "red")
		self.assertLess(after.status.score, before.status.score)
		self.assertEqual(after.risks.open, 1)

	def test_closed_risks_do_not_affect_the_status(self):
		self.new_item(MGR, tracker="Task")
		self.risk(**CRITICAL, status="Closed")
		with self.as_user(MGR):
			data = api.get_project_health(self.ALP, "3m")
		self.assertFalse([r for r in data.status.reasons if r["level"] != "green"])

	def test_hub_and_portfolio_carry_the_risk_counts(self):
		self.new_item(MGR, tracker="Task")
		self.risk(**CRITICAL)
		self.risk(**HIGH)
		with self.as_user(TM):
			hub = api.get_project_hub(self.ALP)
			portfolio = api.get_portfolio("3m")
		self.assertEqual(hub.risks.open, 2)
		row = {p.name: p for p in portfolio.projects}[self.ALP]
		self.assertEqual((row.risks_open, row.risks_critical, row.risks_high), (2, 1, 1))
		self.assertGreaterEqual(portfolio.kpis["risks_open"], 2)

	def test_my_work_lists_the_risks_i_own(self):
		self.risk(title="Mine", **HIGH, risk_owner=DEV)
		self.risk(title="Not mine", **CRITICAL, risk_owner=MGR)
		with self.as_user(DEV):
			rows = my_risks(DEV)
			data = api.get_my_work()
		self.assertEqual([r["title"] for r in rows], ["Mine"])
		self.assertEqual([r["title"] for r in data.risks], ["Mine"])

	def test_client_report_shows_only_the_risks_marked_for_the_client(self):
		self.risk(
			title="Shown to client",
			**HIGH,
			show_in_client_report=1,
			mitigation_plan="<p>Add a second supplier</p>",
		)
		self.risk(title="Internal only", **CRITICAL)
		self.risk(title="Closed one", **HIGH, show_in_client_report=1, status="Closed")
		rows = client_risks(self.ALP)
		self.assertEqual([r["title"] for r in rows], ["Shown to client"])
		self.assertEqual(rows[0]["mitigation"], "Add a second supplier")
		report = build_report(self.ALP, add_days(today(), -7), today())
		html = render_html(report)
		self.assertIn("Risks and mitigation", html)
		self.assertIn("Shown to client", html)
		self.assertNotIn("Internal only", html)

	def test_client_report_has_no_risk_section_without_risks(self):
		report = build_report(self.ALP, add_days(today(), -7), today())
		self.assertNotIn("Risks and mitigation", render_html(report))
