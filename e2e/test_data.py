"""Make or remove labelled test data for the Auri PMS projects (run with the bench env python, from the sites folder).

    ../env/bin/python apps/auri_pms/e2e/test_data.py standard-v16.local make  PROJ-0035 PROJ-0036
    ../env/bin/python apps/auri_pms/e2e/test_data.py standard-v16.local remove

Every record it creates is named "[TEST] ..." and its name is written to ``e2e/test_data_created.json``, so ``remove`` deletes exactly
those records and nothing else. Nothing existing is changed. E-mails and notifications are muted while it runs, and tickets are
assigned only to the manager of the project (no colleague gets a task or a mail from test data).
"""

import json
import sys
from pathlib import Path

import frappe
import frappe.utils
from frappe.utils import add_days, today

TAG = "[TEST]"
LOG = Path(__file__).resolve().parent / "test_data_created.json"
ORDER = [
	"Time Entry",
	"Risk Register",
	"Work Item",
	"Sprint",
	"Release",
	"Project Module",
]  # deletion order, children first


def d(offset: int) -> str:
	return str(add_days(today(), offset))


def log_add(created: dict, doctype: str, name: str) -> str:
	created.setdefault(doctype, []).append(name)
	LOG.write_text(json.dumps(created, indent=1))
	return name


def insert(created: dict, values: dict):
	doc = frappe.get_doc(values)
	doc.flags.ignore_mandatory = False
	doc.insert(ignore_permissions=True)
	log_add(created, doc.doctype, doc.name)
	return doc


def backdate(doctype: str, name: str, days_ago: int) -> None:
	frappe.db.set_value(
		doctype, name, "creation", f"{add_days(today(), -days_ago)} 09:00:00", update_modified=False
	)


def make_project(created: dict, project: str) -> None:
	doc = frappe.get_doc("Project", project)
	manager = next((m.user for m in doc.tracker_members if m.project_role == "Manager"), None)
	if not manager:
		raise SystemExit(f"{project} has no Manager member to assign test tickets to")
	label = doc.tracker_identifier
	prob = frappe.get_meta("Risk Register").get_field("probability").options.split("\n")
	imp = frappe.get_meta("Risk Register").get_field("impact").options.split("\n")

	# ---- modules
	modules = [
		insert(
			created, {"doctype": "Project Module", "project": project, "module_name": f"{TAG} {name}"}
		).name
		for name in ("Billing", "Stock", "Reports")
	]

	# ---- releases: one finished, one overdue, one upcoming
	rel = {}
	for key, due, status in (("R1", -20, "Open"), ("R2", -3, "Open"), ("R3", 12, "Open")):
		rel[key] = insert(
			created,
			{
				"doctype": "Release",
				"project": project,
				"release_name": f"{TAG} {label} {key}",
				"due_date": d(due),
				"status": status,
			},
		).name

	# ---- sprints: one completed, one active, one planned (sprints of a project may not overlap)
	sprints = {}
	plan = {}
	for key, start, end, status in (
		("S1", -28, -15, "Completed"),
		("S2", -3, 10, "Active"),
		("S3", 11, 24, "Planned"),
	):  # clear of any sprint that exists already
		sprints[key] = insert(
			created,
			{
				"doctype": "Sprint",
				"project": project,
				"sprint_name": f"{TAG} {label} {key}",
				"start_date": d(start),
				"end_date": d(end),
				"status": "Planned",
				"goal": "Test data",
			},
		).name
		plan[key] = status

	# ---- tickets: (tracker, subject, priority, release, sprint, module, due, estimate, assigned, client_wait, final status, created days ago, closed days ago)
	rows = [
		("Task", "Set up chart of accounts", "Normal", "R1", "S1", 0, -22, 6, True, False, "Closed", 30, 20),
		(
			"Feature",
			"Sales invoice print format",
			"High",
			"R1",
			"S1",
			0,
			-21,
			10,
			True,
			False,
			"Closed",
			29,
			19,
		),
		("Bug", "Wrong tax on credit note", "Urgent", "R1", "S1", 0, -18, 4, True, False, "Closed", 26, 17),
		(
			"Bug",
			"Stock ledger shows negative balance",
			"Immediate",
			"R2",
			"S2",
			1,
			-2,
			8,
			True,
			False,
			"In Progress",
			12,
			None,
		),
		("Bug", "Report export drops last row", "High", "R2", "S2", 2, -1, 3, True, False, "New", 9, None),
		(
			"Task",
			"Import opening stock",
			"Normal",
			"R2",
			"S2",
			1,
			-4,
			12,
			True,
			False,
			"In Progress",
			11,
			None,
		),
		(
			"Task",
			"Month-end closing checklist",
			"Normal",
			"R2",
			None,
			0,
			-5,
			5,
			False,
			False,
			"New",
			10,
			None,
		),
		(
			"Feature",
			"Batch-wise stock report",
			"High",
			"R3",
			"S2",
			2,
			5,
			16,
			True,
			False,
			"In Progress",
			6,
			None,
		),
		(
			"Feature",
			"Dashboard for collections",
			"Normal",
			"R3",
			"S3",
			2,
			14,
			20,
			False,
			False,
			"New",
			5,
			None,
		),
		(
			"Support",
			"User cannot log in after password reset",
			"Normal",
			None,
			None,
			0,
			2,
			1,
			True,
			False,
			"Resolved",
			4,
			None,
		),
		(
			"Support",
			"Need list of pending approvals",
			"Low",
			None,
			None,
			1,
			8,
			2,
			False,
			True,
			"New",
			8,
			None,
		),
		(
			"Task",
			"Confirm tax registration details",
			"High",
			"R2",
			None,
			0,
			-3,
			2,
			False,
			True,
			"New",
			9,
			None,
		),
		(
			"Bug",
			"Date shows in wrong format on invoice",
			"Low",
			"R3",
			"S2",
			0,
			9,
			2,
			True,
			False,
			"Closed",
			8,
			2,
		),
		("Task", "Train accounts team", "Normal", "R3", "S3", 0, 18, 8, False, False, "New", 3, None),
		(
			"Bug",
			"Customer statement misses credit notes",
			"High",
			None,
			None,
			0,
			-6,
			5,
			True,
			False,
			"Feedback",
			14,
			None,
		),
	]
	items = []
	for (
		tracker,
		subject,
		priority,
		r,
		s,
		mod,
		due,
		est,
		assigned,
		wait,
		final,
		created_ago,
		closed_ago,
	) in rows:
		values = {
			"doctype": "Work Item",
			"project": project,
			"tracker": tracker,
			"subject": f"{TAG} {subject}",
			"priority": priority,
			"status": "New",
			"due_date": d(due),
			"estimated_hours": est,
			"project_module": modules[mod],
			"release": rel[r] if r else None,
			"sprint": sprints[s] if s else None,
			"assigned_to": manager if assigned else None,
		}
		if wait:
			values.update(
				{"dependent_on_client": 1, "client_dependency_note": "Waiting for the client's confirmation"}
			)
		doc = insert(created, values)
		if final != "New":
			doc.reload()
			doc.status = final
			doc.save(ignore_permissions=True)
		if closed_ago is not None:
			frappe.db.set_value(
				"Work Item",
				doc.name,
				"closed_on",
				f"{add_days(today(), -closed_ago)} 12:00:00",
				update_modified=False,
			)
		backdate("Work Item", doc.name, created_ago)
		items.append(doc)

	# ---- the sprints take their final status once their tickets are in (a completed sprint accepts no new ticket)
	for key in ("S1", "S2"):
		for step in ("Active", "Completed"):
			sprint = frappe.get_doc("Sprint", sprints[key])
			if sprint.status == plan[key]:
				break
			try:
				sprint.status = step
				sprint.save(ignore_permissions=True)
			except frappe.ValidationError as e:  # for example another sprint is already active
				print(f"  {sprint.name} stays {sprint.status}: {frappe.utils.strip_html(str(e))[:90]}")
				break

	# ---- time: billable and non-billable over the last three weeks
	hours = [
		(18, 4, 1, "Development"),
		(17, 3, 1, "Testing"),
		(15, 2, 0, "Meeting"),
		(12, 5, 1, "Development"),
		(10, 2, 1, "Functional Support - ERPNext"),
		(8, 3, 0, "Documentation"),
		(6, 4, 1, "Development"),
		(4, 2, 1, "Testing"),
		(3, 1.5, 0, "Client Meeting"),
		(1, 3, 1, "Development"),
	]
	loggable = [
		i for i, row in zip(items, rows, strict=True) if row[10] != "Closed"
	]  # no time can be logged on a closed ticket
	for i, (ago, hrs, billable, activity) in enumerate(hours):
		insert(
			created,
			{
				"doctype": "Time Entry",
				"project": project,
				"work_item": loggable[i % len(loggable)].name,
				"user": manager,
				"date": d(-ago),
				"hours": hrs,
				"is_billable": billable,
				"activity_type": activity,
			},
		)

	# ---- risks
	for title, p, i, status in (
		("Key user may leave before go-live", 3, 4, "Identified"),
		("Data migration may slip", 4, 3, "Mitigating"),
		("Client approvals are slow", 3, 2, "Monitoring"),
	):
		insert(
			created,
			{
				"doctype": "Risk Register",
				"project": project,
				"title": f"{TAG} {title}",
				"status": status,
				"owner": manager,
				"probability": prob[p - 1],
				"impact": imp[i - 1],
				"mitigation_plan": "<p>Test data</p>",
				"due_date": d(10),
			},
		)
	frappe.db.commit()
	print(
		f"{project}: {len(modules)} modules, {len(rel)} releases, {len(sprints)} sprints, {len(items)} tickets, {len(hours)} time entries, 3 risks (assigned to {manager})"
	)


def remove() -> None:
	created = json.loads(LOG.read_text()) if LOG.exists() else {}
	for doctype in ORDER:
		for name in reversed(created.get(doctype, [])):
			if frappe.db.exists(doctype, name):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		print(f"removed {len(created.get(doctype, []))} {doctype}")
	frappe.db.commit()
	LOG.unlink(missing_ok=True)


if __name__ == "__main__":
	site, action, projects = sys.argv[1], sys.argv[2], sys.argv[3:]
	frappe.init(site=site)
	frappe.connect()
	frappe.set_user("Administrator")
	frappe.flags.mute_emails = True
	frappe.flags.in_import = True  # no notifications while seeding
	if action == "make":
		if LOG.exists():
			raise SystemExit(
				f"{LOG.name} exists: run 'remove' first, so the earlier test data is not duplicated"
			)
		created: dict = {}
		for project in projects:
			make_project(created, project)
	elif action == "remove":
		remove()
	else:
		raise SystemExit("make <project>... | remove")
