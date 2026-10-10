# Auri PMS

A simple issue tracker for **ERPNext v16**. Log, assign, track and close work items
(bugs, features, tasks, support requests) against ERPNext Projects, plan them into Releases and log
time against them. One screen to create an item, one list to work from, and no configuration beyond
adding project members.

* Frappe v16 + ERPNext v16 (required app), standard Desk UI only, Frappe Cloud compatible
  (no OS packages, no custom bench commands at runtime).
* Module: **Tracking**. Nothing in Frappe or ERPNext core is modified: everything is added through
  hooks, Custom Fields, Custom DocPerms and `doc_events`.

## Install

```bash
bench get-app https://github.com/anoopverma-collab/Auriga_Track
bench --site <site> install-app auriga_track
bench --site <site> migrate
```

`install-app` loads all fixtures (roles, custom fields on Project and Email Account, workspace,
number cards, charts, reports) and creates the default data **once**: 6 statuses, 3 project roles,
4 trackers (Bug has a workflow), activity types, Tracker Settings and the Kanban board
"Work Items by Status". A later `migrate` never overwrites changes you made to that data.

Uninstall: `bench --site <site> uninstall-app auriga_track` (removes the Project and Email Account
custom fields, the Kanban board, the workspace and the Project permissions it added; ERPNext
Activity Types are left alone).

## Configuration

| Where | What |
|---|---|
| **Tracker Settings** | default status/priority, role used on public projects, close rules (children, blockers), time limits (per entry, per day, lock days), due reminder days, max subtask depth |
| **Work Item Status** | name, sequence, colour, *Is Closed*, default % done; a new status automatically becomes a Kanban column |
| **Ticket Type** | kind of ticket (Bug, Feature, Task, Support): default status, *Counts as Defect*, optional allowed-transition table per project role (empty = everything allowed) |
| **Project Role** | the nine capability flags (create/edit/delete items, manage releases/categories/members, log time, edit others' time, be assigned) |
| **Project > Tracker tab** | identifier (2-10 chars, set once), parent project, public flag, members + role, enabled trackers |
| **Sprint** | project, name, start/end date, goal; status buttons Start / Complete Sprint; Sprint Board (Kanban) and Burndown |
| **Tracker Settings > Weekly Capacity** | working hours per person per week, used by My Work |
| **Email Account** | optional: *Tracker Project* (+ default tracker) turns received mail into work items |

Roles: **Tracker Manager** (and System Manager) administer everything; **Tracker User** sees only the
projects they are a member of, plus public projects. Inside a project the member's **Project Role**
decides what they can do.

## 10-minute quick start

The app opens on the **Project Hub** (there is no home screen; the sidebar and the *Tracker* app icon start there). It lists the projects you are a member of (plus public ones). Open a project to see its tickets, overdue and unassigned counts, the active sprint with burndown, releases, team and time, and to create tickets, sprints and releases already scoped to that project. Views (list, board, Gantt, calendar) and reports open filtered to the project.

Dashboards (all share one theme choice, 8 themes in light and dark, and the *Range* menu: 1 month, 3 months, 6 months, Overall):

| Screen | For | What it shows |
|---|---|---|
| **Project Hub > Health Dashboard** | project manager, client | on track / at risk / off track with reasons, open vs closed, created vs resolved, backlog trend, sprint velocity, ticket aging, spent vs billable hours, tickets waiting on the client |
| **Portfolio** | management | one row per project: health, open, overdue %, done %, budget burn, billable %, tickets waiting on the client; health mix and hour charts |
| **My Work** | everyone | my tickets by due date (overdue / today / this week / later), blocked and client-waiting badges, my sprints, hours this week against the weekly capacity, one-click *Log time* |
| **Quality Dashboard** | QA, project manager | bugs opened vs fixed, critical bugs, time to fix by priority, reopen rate, defects per 100 hours, bugs by category and project (ticket types marked *Counts as Defect*) |
| **Client Status Report** | project manager | a client-ready report for any period: status, delivered, in progress, coming up, risks, *Waiting on you*, plan and hours; email it (logged as *Project Status Report*), download a PDF, or let it go out weekly (Project > Tracker tab: *Report Recipients*, *Send Weekly On*) |

Tick **Dependent on Client** on a ticket (and say what you need): it records *Waiting since*, shows a banner on the ticket and is counted live in the hub, health dashboard, portfolio, My Work and the client report (where the ticket is listed under *Waiting on you*). Tickets waiting on the client are not counted as delivery delays in the project's status.

A daily scheduler job emails each assignee one digest of items that are due within the reminder window
or overdue.

## Development

```bash
bench --site <site> run-tests --app auriga_track          # whole suite
bench --site <site> run-tests --app auriga_track --module auriga_track.tracking.tests.test_workflow
ruff check . && ruff format --check .                      # Python
eslint --ext .js auriga_track                              # JS (default Frappe config)
```

Tests live in `auriga_track/tracking/tests/`, one file per area (see spec ids T-001 ... T-127 in the
docstrings); `utils.py` builds the shared fixture world once per class and isolates every test with a
database savepoint. Business rules live in the DocType controllers and `tracking/utils.py`; client
scripts are UX only.

Design decisions made where the specification was silent are listed in [DECISIONS.md](DECISIONS.md).

## Layout

```
auriga_track/
  hooks.py  install.py  permissions.py
  fixtures/                 custom fields, roles
  public/js/project.js      Tracker tab UX on Project
  tracking/
    utils.py                capabilities, hierarchy, roll-ups, progress formula
    api.py                  get_allowed_statuses, log_time, link queries
    email_intake.py  tasks.py  project_hooks.py
    doctype/ report/ workspace/ number_card/ dashboard_chart/ tests/
```
