"""My Work dashboard."""

import frappe
from frappe.utils import add_days, today

from auri_pms.tracking import api
from auri_pms.tracking.dashboards import get_my_work_data
from auri_pms.tracking.health import monday
from auri_pms.tracking.tests.utils import DEV, MGR, OUT, REP, TrackerTestCase


def days(offset: int) -> str:
	return add_days(today(), offset)


class TestMyWork(TrackerTestCase):
	def mine(self, user=DEV):
		with self.as_user(user):
			return api.get_my_work()

	def test_groups_by_due_date(self):
		"""Open assigned tickets are grouped into overdue, today, this week, later and no date."""
		week_end = monday(frappe.utils.getdate(today())) + frappe.utils.datetime.timedelta(days=6)
		later = add_days(week_end, 3)
		self.new_item(MGR, assigned_to=DEV, due_date=days(-2), subject="late")
		self.new_item(MGR, assigned_to=DEV, due_date=days(0), subject="today")
		self.new_item(MGR, assigned_to=DEV, due_date=later, subject="later")
		self.new_item(MGR, assigned_to=DEV, subject="undated")
		data = self.mine()
		subjects = {k: [i.subject for i in v] for k, v in data.groups.items()}
		self.assertEqual(subjects["overdue"], ["late"])
		self.assertEqual(subjects["today"], ["today"])
		self.assertEqual(subjects["later"], ["later"])
		self.assertEqual(subjects["no_due"], ["undated"])
		self.assertEqual((data.tiles.open, data.tiles.overdue, data.tiles.today), (4, 1, 1))
		self.assertEqual(data.groups.overdue[0].days_overdue, 2)

	def test_only_my_open_tickets(self):
		"""Other people's tickets and closed tickets are not listed."""
		self.new_item(MGR, assigned_to=MGR)
		closed = self.new_item(MGR, tracker="Task", assigned_to=DEV)
		self.save_as(MGR, closed, status="Closed")
		self.assertEqual(self.mine().tiles.open, 0)

	def test_blocked_tickets(self):
		"""A ticket blocked by an open ticket is flagged; once the blocker closes it is not."""
		blocker = self.new_item(MGR, tracker="Task")
		blocked = self.new_item(MGR, tracker="Task", assigned_to=DEV)
		blocked.append("relations", {"relation_type": "Blocked by", "related_work_item": blocker.name})
		self.save_as(MGR, blocked)
		data = self.mine()
		self.assertEqual(data.tiles.blocked, 1)
		self.assertEqual(data.groups.no_due[0].blocked_by, [blocker.name])
		blocker.reload()
		self.save_as(MGR, blocker, status="Closed")
		self.assertEqual(self.mine().tiles.blocked, 0)

	def test_tickets_raised_by_me(self):
		"""Open tickets I raised that someone else works on are listed with the assignee's name."""
		item = self.new_item(DEV, assigned_to=MGR)
		raised = self.mine(DEV).raised
		self.assertEqual([r.name for r in raised], [item.name])
		self.assertTrue(raised[0].assignee_name)

	def test_hours_this_week_and_capacity(self):
		"""Hours per weekday split into billable/non-billable, compared to the weekly capacity."""
		settings = frappe.get_doc("PMS Settings")
		settings.weekly_capacity_hours = 20
		settings.save()
		item = self.new_item(MGR, assigned_to=DEV)
		self.logged_time(DEV, item.name, 4)
		self.logged_time(DEV, item.name, 1, is_billable=0, activity="Meeting")
		data = self.mine()
		today_index = frappe.utils.getdate(today()).weekday()
		self.assertEqual((data.hours.billable[today_index], data.hours.non_billable[today_index]), (4, 1))
		self.assertEqual((data.tiles.hours_week, data.tiles.capacity, data.tiles.capacity_pct), (5, 20, 25))

	def test_missing_days(self):
		"""Weekdays before today without any hours are reported (when the week has such days)."""
		data = self.mine()
		weekday = frappe.utils.getdate(today()).weekday()
		self.assertEqual(len(data.hours.missing_days), min(weekday, 5))

	def test_active_sprints_with_my_tickets(self):
		"""Only active sprints in which I have tickets are shown, with my open/closed share."""
		with self.as_user(MGR):
			sprint = frappe.get_doc(
				{
					"doctype": "Sprint",
					"sprint_name": "S1",
					"project": self.ALP,
					"start_date": days(-2),
					"end_date": days(11),
					"status": "Active",
				}
			).insert()
			other = frappe.get_doc(
				{
					"doctype": "Sprint",
					"sprint_name": "B1",
					"project": self.BET,
					"start_date": days(-2),
					"end_date": days(11),
					"status": "Active",
				}
			).insert()
		self.new_item(MGR, assigned_to=DEV, sprint=sprint.name)
		done = self.new_item(MGR, tracker="Task", assigned_to=DEV, sprint=sprint.name)
		self.save_as(MGR, done, status="Closed")
		self.new_item(MGR, self.BET, sprint=other.name)  # not mine
		sprints = self.mine().sprints
		self.assertEqual([(s.name, s.mine_total, s.mine_closed) for s in sprints], [(sprint.name, 2, 1)])

	def test_closed_by_me(self):
		"""Tickets I closed in the last 4 weeks are counted per week."""
		item = self.new_item(MGR, tracker="Task", assigned_to=DEV)
		self.save_as(DEV, item, status="Closed")
		data = self.mine()
		self.assertEqual((data.tiles.closed_28d, data.closed_weekly[-1]), (1, 1))

	def test_visibility_and_disabled_user(self):
		"""A user only sees tickets of projects they can access; a disabled user sees nothing."""
		item = self.new_item(MGR, self.BET, assigned_to=MGR)
		self.assertEqual(self.mine(OUT).tiles.open, 0)
		self.assertEqual(self.mine(REP).tiles.open, 0)
		frappe.db.set_value("User", MGR, "enabled", 0)
		from auri_pms.tracking.utils import clear_cache

		clear_cache()
		self.assertEqual(self.mine(MGR).tiles.open, 0)
		self.assertTrue(item.name)

	def test_direct_call(self):
		"""The data function works without the API wrapper (used by scheduled jobs)."""
		self.assertEqual(get_my_work_data(DEV)["user"], DEV)
