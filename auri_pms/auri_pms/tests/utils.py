"""Shared fixture world and base class for Auri PMS tests (spec section 8)."""

from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from auri_pms.auri_pms.utils import clear_cache

PASSWORD_FREE_USERS = {
	"tm@test.com": ("Auri PMS Admin",),
	"boss@test.com": ("Auri PMS Manager",),
	"mgr@test.com": ("Auri PMS User",),
	"dev@test.com": ("Auri PMS User",),
	"rep@test.com": ("Auri PMS User",),
	"out@test.com": ("Auri PMS User",),
	"gone@test.com": ("Auri PMS User",),
}
TM, BOSS, MGR, DEV, REP, OUT, GONE = (
	"tm@test.com",
	"boss@test.com",
	"mgr@test.com",
	"dev@test.com",
	"rep@test.com",
	"out@test.com",
	"gone@test.com",
)


def make_user(email: str, roles: tuple[str, ...]) -> None:
	"""Create an enabled user with the given roles unless it exists."""
	if frappe.db.exists("User", email):
		return
	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"send_welcome_email": 0,
			"enabled": 1,
			"roles": [{"role": r} for r in roles],
		}
	).insert(ignore_permissions=True)


def ensure_company(force_create: bool = False) -> str:
	"""A Company for the Projects the tests create (ERPNext requires one; a fresh CI site has none)."""
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if company and not force_create:
		frappe.defaults.set_global_default("company", company)
		return company
	# a site that skipped the ERPNext setup wizard lacks this master, which Company creation links to
	if not frappe.db.exists("Warehouse Type", "Transit"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": "Auri PMS Test Company",
			"abbr": "ATTC",
			"default_currency": "INR",
			"country": "India",
		}
	).insert(ignore_permissions=True)
	frappe.defaults.set_global_default("company", company.name)
	return company.name


def make_project(
	name: str,
	identifier: str | None,
	members: list[tuple[str, str]],
	public: bool = False,
	trackers: list[str] | None = None,
) -> str:
	"""Create a Project with tracker data and return its name."""
	doc = frappe.get_doc(
		{
			"doctype": "Project",
			"company": ensure_company(),
			"project_name": name,
			"pms_enabled": 1 if identifier else 0,
			"tracker_identifier": identifier,
			"is_public": 1 if public else 0,
			# the health status is off by default; the fixture projects show it so the dashboards can be tested
			"show_health_hub": 1,
			"show_health_portfolio": 1,
			"show_health_report": 1,
			"tracker_members": [{"user": u, "project_role": r} for u, r in members],
			"enabled_trackers": [{"tracker": t} for t in (trackers or [])],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def ensure_outgoing_account() -> None:
	"""Make sure emails can be queued (a default outgoing Email Account exists)."""
	if frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}):
		return
	frappe.get_doc(
		{
			"doctype": "Email Account",
			"email_account_name": "Tracker Test Outgoing",
			"email_id": "tracker-test@example.com",
			"enable_outgoing": 1,
			"default_outgoing": 1,
			"smtp_server": "localhost",
			"smtp_port": 25,
			"awaiting_password": 0,
			"password": "not-used",
		}
	).insert(ignore_permissions=True)


def flags_all() -> list[str]:
	"""The capability checkboxes of a Project Role."""
	from auri_pms.auri_pms.utils import CAPABILITY_FIELDS

	return list(CAPABILITY_FIELDS)


def build_world() -> frappe._dict:
	"""Create the shared fixture world (spec section 8) and return its record names."""
	ensure_outgoing_account()
	for email, roles in PASSWORD_FREE_USERS.items():
		make_user(email, roles)
	alp = make_project(
		"Project Alpha", "ALP", [(MGR, "Manager"), (DEV, "Developer"), (REP, "Reporter"), (GONE, "Developer")]
	)
	bet = make_project("Project Beta", "BET", [(MGR, "Manager")], public=True, trackers=["Bug", "Task"])
	gam = make_project("Project Gamma", None, [])
	releases = {}
	for name, status in (("v1", "Open"), ("v0", "Locked"), ("v2", "Closed")):
		doc = frappe.get_doc({"doctype": "Release", "release_name": name, "project": alp, "status": "Open"})
		doc.insert(ignore_permissions=True)
		if status != "Open":
			doc.status = status
			doc.save(ignore_permissions=True)
		releases[name] = doc.name
	frappe.db.set_single_value("PMS Settings", "max_hours_per_day", 12)
	# the shipped penalties, so a site that tuned its own does not change what the tests expect
	frappe.db.set_single_value("PMS Settings", {"score_red_penalty": 25, "score_amber_penalty": 10})
	frappe.get_doc("User", GONE).update({"enabled": 0}).save(ignore_permissions=True)
	clear_cache()
	return frappe._dict(alp=alp, bet=bet, gam=gam, releases=releases)


class TrackerTestCase(IntegrationTestCase):
	SHOW_TRANSACTION_COMMIT_WARNINGS = True
	"""Base class: builds the world once per class and isolates every test with a savepoint."""

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.world = build_world()
		cls.ALP, cls.BET, cls.GAM = cls.world.alp, cls.world.bet, cls.world.gam

	def setUp(self) -> None:
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.savepoint("track_test")
		self.use_shipped_defaults()
		clear_cache()

	def set_see_all(self, value: bool, role: str = "Developer") -> None:
		"""Project Role > Can See All Work Items for ``role`` (within this test only)."""
		frappe.db.set_value("Project Role", role, "can_see_all_items", int(value))
		clear_cache()

	def use_shipped_defaults(self) -> None:
		"""Within this test only (the savepoint is rolled back): the statuses and Project Role capabilities the app installs.

		A site that added a status (for example "Dev complete") or tuned a role would otherwise change what the tests expect."""
		from auri_pms.install import PROJECT_ROLES, STATUSES

		shipped = {s[0] for s in STATUSES}
		for name in frappe.get_all("Work Item Status", pluck="name"):
			frappe.db.set_value("Work Item Status", name, "is_active", int(name in shipped))
		for role, flags in PROJECT_ROLES.items():
			if frappe.db.exists("Project Role", role):
				frappe.db.set_value("Project Role", role, {f: int(f in flags) for f in flags_all()})

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="track_test")
		clear_cache()
		super().tearDown()

	# helpers ------------------------------------------------------------------
	@contextmanager
	def as_user(self, user: str):
		"""Run a block as ``user`` and restore Administrator afterwards."""
		frappe.set_user(user)
		clear_cache()
		try:
			yield
		finally:
			frappe.set_user("Administrator")
			clear_cache()

	def new_item(self, user: str = DEV, project: str | None = None, **kw):
		"""Insert a Work Item as ``user`` and return the document."""
		values = {
			"doctype": "Work Item",
			"subject": kw.pop("subject", "Test item"),
			"project": project or self.ALP,
			"tracker": kw.pop("tracker", "Bug"),
			**kw,
		}
		with self.as_user(user):
			return frappe.get_doc(values).insert()

	def save_as(self, user: str, doc, **changes):
		"""Update ``doc`` fields and save it as ``user``."""
		with self.as_user(user):
			doc.update(changes)
			doc.save(ignore_version=False)  # Frappe skips Version rows in tests unless asked
		return doc

	def assertThrows(self, text: str, fn, exc=frappe.ValidationError):
		"""Assert ``fn()`` raises ``exc`` whose message contains ``text``."""
		with self.assertRaises(exc) as cm:
			fn()
		self.assertIn(text, str(cm.exception))

	def logged_time(
		self, user, work_item=None, hours=1, project=None, date=None, activity="Development", **kw
	):
		"""Insert a Time Entry as ``user``."""
		kw.setdefault("comment", "Worked on it")  # a comment is required on every entry
		with self.as_user(user):
			return frappe.get_doc(
				{
					"doctype": "Time Entry",
					"work_item": work_item,
					"project": project,
					"user": kw.pop("entry_user", user),
					"date": date or today(),
					"hours": hours,
					"activity_type": activity,
					**kw,
				}
			).insert()


def days_ago(n: int) -> str:
	"""Return the ISO date ``n`` days ago."""
	return add_days(today(), -n)
