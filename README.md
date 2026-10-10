<p align="center"><img src="docs/logo.png" alt="Auri PMS logo" width="140"></p>

# Auri PMS

**Project Management System** &middot; *Plan. Track. Deliver.*

[![CI](https://github.com/anoopverma-collab/Auri_PMS/actions/workflows/ci.yml/badge.svg)](https://github.com/anoopverma-collab/Auri_PMS/actions/workflows/ci.yml)

A centralized platform for project planning, task management, timelines, effort tracking, team collaboration and delivery monitoring, built for **ERPNext v16**. Suitable for projects, tasks, milestones, timesheets, estimates versus actuals and management dashboards. Log, assign, track and close work items (bugs, features, tasks, support requests) against ERPNext Projects, plan them into sprints and releases, log time against them and report progress to clients. One screen to create an item, one list to work from, and no configuration beyond adding project members.

* Frappe v16 + ERPNext v16 (required app), standard Desk UI only, Frappe Cloud compatible
  (no OS packages, no custom bench commands at runtime).
* Module: **Tracking**. Nothing in Frappe or ERPNext core is modified: everything is added through
  hooks, Custom Fields, Custom DocPerms and `doc_events`.

## Features

| Area | What you get |
|---|---|
| Tickets (Work Items) | bugs, features, tasks and support requests with parent/child tickets, priorities, categories, start/due dates, estimates, relations and blockers; per-project ticket numbers such as `SJDM-00001` |
| Ticket Types and workflow | configurable ticket types with default status, *Counts as Defect* flag and allowed status transitions per project role |
| Project Hub | project-first screen: users only see projects they belong to (or public ones) and work inside the chosen project |
| Roles and access | project roles with nine capability flags; private projects stay hidden from outsiders |
| Sprints | start/end dates, goal, add tickets to a sprint, Start / Complete, Sprint Board and Burndown |
| Releases | group tickets into versions with progress and due date |
| Kanban board | one column per status, drag a ticket to change its status (blocked moves are refused) |
| Gantt chart | tickets drawn from start date to due date, filtered to the project |
| Time tracking | log hours per ticket with activity type and a *Billable* flag; limits per entry/day and lock days |
| Dependent on Client | tick a ticket that waits on the client; tracked with a note and *Waiting since* and counted everywhere |
| Dashboards | Project Health, Portfolio, My Work, Quality and Client Status Report |
| Themes and range | 8 themes in light and dark and a 1 month / 3 months / 6 months / Overall range, shared by all dashboards |
| Reports | Work Item Summary, Time Log Summary, Release Progress, Overdue Work Items, Sprint Summary, Sprint Burndown, Client Dependencies |
| Email | email a project's status report (preview, PDF, weekly schedule), daily due-date digests, optional email-to-ticket intake |

## Screenshots

All screenshots use the sample SJDM Implementation project data. Every screen is shown in **light** and **dark** mode: the app follows Frappe's own light/dark setting (user menu, *Toggle Theme*), so nothing needs configuring.

### Project Hub

The starting point. It lists only the projects you belong to (plus public ones); each card shows open, overdue, your own tickets, team size and the active sprint. Open a project to work inside it.

<table><tr><td width="50%"><img src="docs/screenshots/light/01-project-hub.png" alt="Project Hub (light)"></td><td width="50%"><img src="docs/screenshots/dark/01-project-hub.png" alt="Project Hub (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Project overview

One project's workbench: open, overdue, assigned to me, unassigned, backlog, closed, waiting-on-client and hours; the active sprint with its burndown; open tickets by status and type; the tickets waiting on the client; sprints, releases, team and recent tickets. The *Views* and *Reports* menus open the list, Kanban, Gantt and reports already filtered to this project.

<table><tr><td width="50%"><img src="docs/screenshots/light/02-project-overview.png" alt="Project overview (light)"></td><td width="50%"><img src="docs/screenshots/dark/02-project-overview.png" alt="Project overview (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Project Health

The client-facing health view. The banner gives the status (On Track, At Risk or Off Track), a score and every reason behind it. Below it: complete %, open and closed tickets, overdue, waiting on the client, hours spent, billable hours, created vs resolved, backlog trend, ageing, sprint velocity and estimated vs spent hours. Use the *Range* menu for 1 month, 3 months, 6 months or overall.

<table><tr><td width="50%"><img src="docs/screenshots/light/03-project-health.png" alt="Project Health (light)"></td><td width="50%"><img src="docs/screenshots/dark/03-project-health.png" alt="Project Health (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Portfolio

Every project you can see on one screen, for management. The banner summarises the health of the projects that have the Portfolio switch ticked, and the table compares open tickets, overdue %, done %, budget burn, billable % and client-waiting tickets. Click a project to open its health view.

<table><tr><td width="50%"><img src="docs/screenshots/light/04-portfolio.png" alt="Portfolio (light)"></td><td width="50%"><img src="docs/screenshots/dark/04-portfolio.png" alt="Portfolio (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### My Work

A personal page for the signed-in user: open tickets grouped by due date (overdue, today, this week, later), what is blocked or waiting on the client, hours logged this week against the weekly capacity, active sprints, and one-click *Log time*.

<table><tr><td width="50%"><img src="docs/screenshots/light/05-my-work.png" alt="My Work (light)"></td><td width="50%"><img src="docs/screenshots/dark/05-my-work.png" alt="My Work (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Quality dashboard

Bug quality across projects: bugs opened vs fixed, critical open bugs, time to fix by priority, reopen rate, bugs per 100 hours, bugs by category and project, and the age of open bugs. A ticket type counts as a bug when *Counts as Defect* is ticked.

<table><tr><td width="50%"><img src="docs/screenshots/light/06-quality.png" alt="Quality Dashboard (light)"></td><td width="50%"><img src="docs/screenshots/dark/06-quality.png" alt="Quality Dashboard (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Client Status Report

A client-ready report for any period, previewed exactly as it will be emailed or exported to PDF: status, delivered tickets, what is in progress, what is waiting on the client, hours, plan and risks. Email it, download the PDF, or let it go out weekly. Every send is logged.

<table><tr><td width="50%"><img src="docs/screenshots/light/07-client-status-report.png" alt="Client Status Report (light)"></td><td width="50%"><img src="docs/screenshots/dark/07-client-status-report.png" alt="Client Status Report (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Client Dependencies report

The drill-down behind every *Waiting on client* number: each open ticket that depends on the client, how long it has waited and what is needed. Tick *Dependent on Client* on a ticket to put it here.

<table><tr><td width="50%"><img src="docs/screenshots/light/08-client-dependencies-report.png" alt="Client Dependencies report (light)"></td><td width="50%"><img src="docs/screenshots/dark/08-client-dependencies-report.png" alt="Client Dependencies report (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Kanban board

One column per ticket status. Drag a card to change its status; a move the workflow does not allow is refused.

<table><tr><td width="50%"><img src="docs/screenshots/light/09-kanban-board.png" alt="Kanban board (light)"></td><td width="50%"><img src="docs/screenshots/dark/09-kanban-board.png" alt="Kanban board (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Gantt chart

Each ticket drawn from its start date to its due date, so overlaps and slips are visible. Zoom with the Quarter Day, Day, Week, Month and Year buttons.

<table><tr><td width="50%"><img src="docs/screenshots/light/10-gantt-chart.png" alt="Gantt chart (light)"></td><td width="50%"><img src="docs/screenshots/dark/10-gantt-chart.png" alt="Gantt chart (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

## App themes

The dashboards (Project Hub, Project Health, Portfolio, My Work, Quality and Client Status Report) share one theme. Pick it from the **Theme** menu at the top right of any dashboard; the choice applies to all of them and is remembered in your browser. The 1 month / 3 months / 6 months / Overall **Range** menu is shared the same way.

Every theme has a light and a dark version. The version follows Frappe's own light/dark setting, so a user who switches Frappe to dark mode gets the dark version of the chosen theme. Forms, lists and the rest of Desk keep the standard Frappe look.

| Theme | Look | Light | Dark |
|---|---|---|---|
| **Glass + Soft** | Frosted-glass cards over a soft colour gradient. The default theme. | <img src="docs/screenshots/light/theme-glass.png" width="260" alt="Glass + Soft light"> | <img src="docs/screenshots/dark/theme-glass.png" width="260" alt="Glass + Soft dark"> |
| **Soft UI (Neumorphism)** | Cards that look raised out of the page with soft light and dark shadows on a single grey colour. | <img src="docs/screenshots/light/theme-soft.png" width="260" alt="Soft UI (Neumorphism) light"> | <img src="docs/screenshots/dark/theme-soft.png" width="260" alt="Soft UI (Neumorphism) dark"> |
| **Soft UI - Convex** | Soft UI with slightly domed cards: a light-to-dark gradient across each surface for a tactile feel. | <img src="docs/screenshots/light/theme-soft-convex.png" width="260" alt="Soft UI - Convex light"> | <img src="docs/screenshots/dark/theme-soft-convex.png" width="260" alt="Soft UI - Convex dark"> |
| **Soft UI - Pressed** | Soft UI where panels are sunk into the page like trays while the number tiles stay raised. | <img src="docs/screenshots/light/theme-soft-pressed.png" width="260" alt="Soft UI - Pressed light"> | <img src="docs/screenshots/dark/theme-soft-pressed.png" width="260" alt="Soft UI - Pressed dark"> |
| **Soft UI - Glow** | Soft UI where every tile glows in its own colour; strongest in dark mode, good for wall displays. | <img src="docs/screenshots/light/theme-soft-glow.png" width="260" alt="Soft UI - Glow light"> | <img src="docs/screenshots/dark/theme-soft-glow.png" width="260" alt="Soft UI - Glow dark"> |
| **Soft UI - Pearl** | Soft UI with a glossy sheen and a bright top edge for a clean, polished look. | <img src="docs/screenshots/light/theme-soft-pearl.png" width="260" alt="Soft UI - Pearl light"> | <img src="docs/screenshots/dark/theme-soft-pearl.png" width="260" alt="Soft UI - Pearl dark"> |
| **Minimal Clean** | Plain white (or near-black) cards with thin borders and no effects. | <img src="docs/screenshots/light/theme-minimal.png" width="260" alt="Minimal Clean light"> | <img src="docs/screenshots/dark/theme-minimal.png" width="260" alt="Minimal Clean dark"> |
| **Flat - Solid colour** | No shadows or gradients; every number tile is a solid block of colour. | <img src="docs/screenshots/light/theme-flat-solid.png" width="260" alt="Flat - Solid colour light"> | <img src="docs/screenshots/dark/theme-flat-solid.png" width="260" alt="Flat - Solid colour dark"> |

## Install

```bash
bench get-app https://github.com/anoopverma-collab/Auri_PMS
bench --site <site> install-app auri_pms
bench --site <site> migrate
```

`install-app` loads all fixtures (roles, custom fields on Project and Email Account, workspace,
number cards, charts, reports) and creates the default data **once**: 6 statuses, 3 project roles,
4 ticket types (Bug has a workflow), activity types, Tracker Settings and the Kanban board
"Work Items by Status". A later `migrate` never overwrites changes you made to that data.

Uninstall: `bench --site <site> uninstall-app auri_pms` (removes the Project and Email Account
custom fields, the Kanban board, the workspace and the Project permissions it added; ERPNext
Activity Types are left alone).

## Configuration

| Where | What |
|---|---|
| **Tracker Settings** | default status/priority, role used on public projects, close rules (children, blockers), time limits (per entry, per day, lock days), due reminder days, max subtask depth |
| **Work Item Status** | name, sequence, colour, *Is Closed*, default % done; a new status automatically becomes a Kanban column |
| **Ticket Type** | kind of ticket (Bug, Feature, Task, Support): default status, *Counts as Defect*, optional allowed-transition table per project role (empty = everything allowed) |
| **Project Role** | the nine capability flags (create/edit/delete items, manage releases/categories/members, log time, edit others' time, be assigned) |
| **Project > Auri PMS tab** | identifier (2-10 chars, set once), parent project, public flag, members + role, enabled ticket types | 
| **Project > Auri PMS tab > Health Status** | three checkboxes (all off by default) that show or hide the health status (On Track / At Risk / Off Track, score, reasons) on the Project Hub health dashboard, the Portfolio and the Client Status Report (email, PDF). Counts and charts are always shown |
| **Sprint** | project, name, start/end date, goal; status buttons Start / Complete Sprint; Sprint Board (Kanban) and Burndown |
| **Tracker Settings > Weekly Capacity** | working hours per person per week, used by My Work |
| **Email Account** | optional: *Tracker Project* (+ default ticket type) turns received mail into work items |

Roles: **Tracker Manager** (and System Manager) administer everything; **Tracker User** sees only the
projects they are a member of, plus public projects. Inside a project the member's **Project Role**
decides what they can do.

## 10-minute quick start

The app opens on the **Project Hub** (there is no home screen; the sidebar and the *Auri PMS* app icon start there). It lists the projects you are a member of (plus public ones). Open a project to see its tickets, overdue and unassigned counts, the active sprint with burndown, releases, team and time, and to create tickets, sprints and releases already scoped to that project. Views (list, board, Gantt, calendar) and reports open filtered to the project.

Dashboards (all share one theme choice, 8 themes in light and dark, and the *Range* menu: 1 month, 3 months, 6 months, Overall):

| Screen | For | What it shows |
|---|---|---|
| **Project Hub > Health Dashboard** | project manager, client | On Track / At Risk / Off Track with reasons, open vs closed, created vs resolved, backlog trend, sprint velocity, ticket aging, spent vs billable hours, tickets waiting on the client |
| **Portfolio** | management | a status banner like the other dashboards (worst health, average score and the projects that need attention, for projects with the Portfolio switch ticked) and one row per project: health, open, overdue %, done %, budget burn, billable %, tickets waiting on the client; ticket, budget, flow and hour charts |
| **My Work** | everyone | my tickets by due date (overdue / today / this week / later), blocked and client-waiting badges, my sprints, hours this week against the weekly capacity, one-click *Log time* |
| **Quality Dashboard** | QA, project manager | bugs opened vs fixed, critical bugs, time to fix by priority, reopen rate, defects per 100 hours, bugs by category and project (ticket types marked *Counts as Defect*) |
| **Client Dependencies** (report) | project manager | every open ticket waiting on the client, how long, and what is needed; opened from the *Waiting on client* tiles |
| **Client Status Report** | project manager | a client-ready report for any period: status, delivered, in progress, coming up, risks, *Waiting on you*, plan and hours; email it (logged as *Project Status Report*), download a PDF, or let it go out weekly (Project > Auri PMS tab: *Report Recipients*, *Send Weekly On*) |

Tick **Dependent on Client** on a ticket (and say what you need): it records *Waiting since*, shows a banner on the ticket and is counted live in the hub, health dashboard, portfolio, My Work and the client report (where the ticket is listed under *Waiting on you*). Tickets waiting on the client are not counted as delivery delays in the project's status.

A daily scheduler job emails each assignee one digest of items that are due within the reminder window
or overdue.

## Development

```bash
bench --site <site> run-tests --app auri_pms          # whole suite
bench --site <site> run-tests --app auri_pms --module auri_pms.tracking.tests.test_workflow
ruff check . && ruff format --check .                      # Python
eslint --ext .js auri_pms                              # JS (default Frappe config)
```

Tests live in `auri_pms/tracking/tests/`, one file per area (215 tests at the time of writing); `utils.py` builds the shared fixture world once per class and isolates every test with a
database savepoint. Business rules live in the DocType controllers and `tracking/utils.py`; client
scripts are UX only.

Design decisions made where the specification was silent are listed in [DECISIONS.md](DECISIONS.md).

## Layout

```
auri_pms/
  hooks.py  install.py  permissions.py  patches/
  fixtures/                 custom fields, roles
  public/js/                auri_hub.bundle.js (shared dashboard UI and themes), auri_pms.bundle.js, project.js
  workspace_sidebar/  desktop_icon/
  tracking/
    utils.py                capabilities, hierarchy, roll-ups, progress formula
    api.py                  hub, health, portfolio, My Work and quality endpoints, log_time, link queries
    health.py  dashboards.py  status_report.py
    email_intake.py  tasks.py  project_hooks.py
    doctype/                Work Item, Sprint, Release, Time Entry, Ticket Type, Project Role, ...
    page/                   project_hub, portfolio, my_work, quality_dashboard, status_report
    report/                 work item, time log, release, sprint and client dependency reports
    tests/
```
