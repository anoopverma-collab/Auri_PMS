<p align="center"><img src="docs/logo.png" alt="Auri PMS logo" width="140"></p>

# Auri PMS

**Project Management System**

[![CI](https://github.com/anoopverma-collab/Auri_PMS/actions/workflows/ci.yml/badge.svg)](https://github.com/anoopverma-collab/Auri_PMS/actions/workflows/ci.yml)

A centralized platform for project planning, task management, timelines, effort tracking, team collaboration and delivery monitoring, built for **ERPNext v16**. Suitable for projects, tasks, milestones, timesheets, estimates versus actuals and management dashboards, with a risk register, project health status and client status reports (choice of email layouts, sections you can switch and reorder, defaults in PMS Settings, PDF and delivery tracking). Log, assign, track and close work items (bugs, features, tasks, support requests) against ERPNext Projects, plan them into sprints and releases, log time against them and report progress to clients. One screen to create an item, one list to work from, and no configuration beyond adding project members.

* Frappe v16 + ERPNext v16 (required app), standard Desk UI only, Frappe Cloud compatible
  (no OS packages, no custom bench commands at runtime).
* Module: **Auri PMS**. Nothing in Frappe or ERPNext core is modified: everything is added through
  hooks, Custom Fields, Custom DocPerms and `doc_events`.

## Features

| Area | What you get |
|---|---|
| Tickets (Work Items) | bugs, features, tasks and support requests with parent/child tickets, priorities, categories, start/due dates, estimates, relations and blockers; per-project ticket numbers such as `AURI-00001` |
| Ticket Types and workflow | configurable ticket types with default status, *Counts as Defect* flag and allowed status transitions per project role |
| Project Hub | project-first screen: users only see projects they belong to (or public ones) and work inside the chosen project |
| Roles and access | three roles (Auri PMS Admin, Manager, User) and project roles with nine capability flags; managers and users see only their own projects; private projects stay hidden from outsiders |
| Allocation | each member's Allocation % of the weekly capacity, logged vs allocated hours per project, and team capacity with over-allocation and burnout flags |
| Sprints | start/end dates, goal, add tickets to a sprint, Start / Complete, Sprint Board and Burndown |
| Releases | group tickets into versions with progress and due date |
| Modules | tag every ticket with the module (part of the product) it is for, such as Sales, Stock or Accounts; dashboards, reports and the client report break the numbers down by module |
| Risk Register | one record per project risk with probability x impact scoring (Low, Medium, High, Critical), owner, mitigation plan and due date; open risks feed the project health status, the dashboards and the client report |
| Kanban board | one column per status, drag a ticket to change its status (blocked moves are refused) |
| Gantt chart | tickets drawn from start date to due date, filtered to the project |
| Time tracking | log hours per ticket with activity type and a *Billable* flag; limits per entry/day and lock days |
| Dependent on Client | tick a ticket that waits on the client; tracked with a note and *Waiting since* and counted everywhere |
| Dashboards | Project Health (with a risk heat map and tickets by module), Portfolio (billing, team capacity, notes and a period table), My Work (greeting, focus list, risks I own), Quality (bugs by module) and Client Status Report (progress by module, risks and mitigation) |
| Themes and range | 8 themes in light and dark and a 1 month / 3 months / 6 months / Overall range, shared by all dashboards |
| Reports | Work Item Summary, Time Log Summary, Release Progress, Overdue Work Items, Sprint Summary, Sprint Burndown, Client Dependencies |
| Email | email a project's status report (choice of layouts, sections you can switch and drag into order, tickets you can remove or add with a note, preview, PDF, weekly and monthly schedule, delivery tracking), daily due-date digests, optional email-to-ticket intake |

## Screenshots

All screenshots use the sample Auriga project data. Every screen is shown in **light** and **dark** mode: the app follows Frappe's own light/dark setting (user menu, *Toggle Theme*), so nothing needs configuring.

### Project Hub

The starting point. It lists only the projects you belong to (plus public ones); each card shows open, overdue, your own tickets, team size and the active sprint. Open a project to work inside it.

<table><tr><td width="50%"><img src="docs/screenshots/light/01-project-hub.png" alt="Project Hub (light)"></td><td width="50%"><img src="docs/screenshots/dark/01-project-hub.png" alt="Project Hub (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Project overview

One project's workbench, laid out in aligned rows: the sprint with its burndown next to open tickets by status and type; tickets waiting on the client and open tickets by module next to the risk register; sprints, releases and team side by side; and the 10 most recently changed tickets. The *Views* and *Reports* menus open the list, Kanban, Gantt, risk register and reports already filtered to this project.

<table><tr><td width="50%"><img src="docs/screenshots/light/02-project-overview.png" alt="Project overview (light)"></td><td width="50%"><img src="docs/screenshots/dark/02-project-overview.png" alt="Project overview (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Project Health

The health view for one project. The header gives the health score and status (On Track, At Risk or Off Track) with the reasons behind it, opened from *How is it worked out?*, the key figures (complete %, open and overdue, hours spent, billable hours) and a notes button with the latest note. Numbered sections follow: Delivery (created vs resolved, backlog trend), Open work (by status, priority and age), Breakdown (by type and module), Client and effort (waiting on the client, estimated vs spent), Risk (probability x impact heat map and the top open risks), Billing and time (Billing graph, billable vs non-billable tickets, time by ticket category, hours by activity), People (team load and burnout risk, hours and open tickets by person), Plan (sprint velocity, releases) and a final *Tickets and billable time by period* table (Overall, last 7, 30 and 90 days, this year, custom range). Every count opens its tickets or time entries. Use the *Range* menu for 1 month, 3 months, 6 months or overall.

<table><tr><td width="50%"><img src="docs/screenshots/light/03-project-health.png" alt="Project Health (light)"></td><td width="50%"><img src="docs/screenshots/dark/03-project-health.png" alt="Project Health (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### Portfolio

Every project you can see on one screen, for management (Auri PMS Admins see all projects, managers the ones they manage). Pick projects in the search box and press *Apply* to focus everything on them until you press *Show all*. It shows the health banner, project cards and a table comparing open tickets, overdue %, done %, budget burn, billable % and client-waiting tickets, trends by project, a Billing graph, billable vs non-billable tickets, time by ticket category, budget burn, risks, team capacity with over-allocation and burnout flags, a *Tickets and billable time by period* table and a notes button per project. Every count is clickable; click a project to open its health view.

<table><tr><td width="50%"><img src="docs/screenshots/light/04-portfolio.png" alt="Portfolio (light)"></td><td width="50%"><img src="docs/screenshots/dark/04-portfolio.png" alt="Portfolio (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

### My Work

A personal page for the signed-in user: a greeting for the time of day, rings for the week's hours, tickets on time, sprint progress and billable share, a focus list for today, open tickets grouped by due date (overdue, today, this week, later) with an *Open list* link per group, what is blocked or waiting on the client, hours logged this week against the weekly capacity, active sprints, releases and projects you are on, and one-click *Log time*. Every count opens its list.

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

### Risk Register

One record per project risk. Probability and impact are each scored 1 to 5, the score is their product, and the level follows from it (Low 1-4, Medium 5-9, High 10-14, Critical 15-25). Each risk has an owner, a status (Identified, Mitigating, Monitoring, Occurred, Closed), a mitigation plan and due date, a contingency plan and an optional related ticket. Open risks lower the project health status and appear on the project overview, Project Health, Portfolio and My Work; risks ticked *Show in Client Status Report* are listed with their mitigation in the client report.

<table><tr><td width="50%"><img src="docs/screenshots/light/11-risk-register-list.png" alt="Risk Register list (light)"></td><td width="50%"><img src="docs/screenshots/dark/11-risk-register-list.png" alt="Risk Register list (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

<table><tr><td width="50%"><img src="docs/screenshots/light/12-risk-register-form.png" alt="Risk Register form (light)"></td><td width="50%"><img src="docs/screenshots/dark/12-risk-register-form.png" alt="Risk Register form (dark)"></td></tr><tr><td align="center"><sub>Light mode</sub></td><td align="center"><sub>Dark mode</sub></td></tr></table>

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
4 ticket types (Bug has a workflow), activity types, PMS Settings and the Kanban board
"Work Items by Status". A later `migrate` never overwrites changes you made to that data.

The status report PDF needs `wkhtmltopdf` on the server. CI runs on Ubuntu 24.04 for that reason, as the `wkhtmltopdf` package
is missing from Ubuntu 26.04 (`ubuntu-latest`).

Uninstall: `bench --site <site> uninstall-app auri_pms` (removes the Project and Email Account
custom fields, the Kanban board, the workspace and the Project permissions it added; ERPNext
Activity Types are left alone).

## Configuration

| Where | What |
|---|---|
| **PMS Settings** | default status/priority, role used on public projects, close rules (children, blockers), **Members See All Work Items** (ticked by default: a member sees every ticket of their projects; unticked: only the tickets assigned to them, as Assigned To or Additional Assignee; admins and members whose Project Role can manage members still see all), time limits (per entry, per day, lock days), due reminder days, max subtask depth; *Closed Tickets and Sprints* (three switches, all but the first off by default): **Keep Closed On Visible and Editable** (edit *Closed On* on a ticket and keep a date typed while closing), **Allow Completed Sprint for Closed Tickets** (a closed ticket may be moved to a Completed sprint) and **Allow Reopening a Completed Sprint** (adds *Reopen Sprint*) |
| **PMS Settings > Risk & Health** | the Medium, High and Critical risk score levels and every project health threshold and score penalty (see *How the health status is worked out*) |
| **PMS Settings > Status Report** | default Email Template, which sections the report includes, the Section Order table, default recipients and default subject (see *Client Status Report: layouts, sections and defaults*) |
| **Work Item Status** | name, sequence, colour, *Is Closed*, default % done; a new status automatically becomes a Kanban column |
| **Ticket Type** | kind of ticket (Bug, Feature, Task, Support): default status, *Counts as Defect*, optional allowed-transition table per project role (empty = everything allowed) |
| **Project Role** | the nine capability flags (create/edit/delete items, manage releases/categories/members, log time, edit others' time, be assigned) |
| **Project > Auri PMS tab** | *Project* (identifier, 2-10 chars set once; parent project; budget hours; public flag), *Members* + role, *Ticket Types*, *Client Status Report* (recipients, CC, weekly/monthly schedule), *Health Status* and *Custom Fields* (a count of 1-10 and that many text fields, three to a row) |
| **Work Item** | besides the usual fields: **Additional Assignees** (more people on a ticket: each must be a member who can be assigned, gets a ToDo, and sees the ticket in My Work and the due digest; *Assigned To* stays the main assignee and the other dashboards count only that person), **Project Custom Fields** (the project's Custom 1-10 copied to the ticket, editable, usable as list columns and filters; a changed project value reaches tickets that still hold the old one) |
| **Project > Auri PMS tab > Health Status** | three checkboxes (all off by default) that show or hide the health status (On Track / At Risk / Off Track, score, reasons) on the Project Hub health dashboard, the Portfolio and the Client Status Report (email, PDF). Counts and charts are always shown |
| **Project Module** | the modules of a project (name, optional lead); project managers maintain them and tickets pick one in the *Module* field |
| **Risk Register** | project, risk, category, owner, probability and impact (1-5 each; the score is the product), status (Identified, Mitigating, Monitoring, Occurred, Closed), mitigation due date, mitigation and contingency plan, related ticket, and *Show in Client Status Report*; anyone who can create tickets in the project can raise and edit risks, project managers delete them |
| **Sprint** | project, name, start/end date, goal; status buttons Start / Complete Sprint (and Reopen Sprint when the PMS Settings switch is on, only while no other sprint of the project is Active); Sprint Board (Kanban) and Burndown |
| **PMS Settings > Weekly Capacity** | working hours per person per week, used by My Work |
| **Email Account** | optional: *Auri PMS Project* (+ default ticket type) turns received mail into work items |

### Project settings: Enable Auri PMS, Client Status Report and Health Status

All of this is on the **Auri PMS tab of the Project** form.

**Enable Auri PMS** - tick it to manage a project in Auri PMS; the rest of the tab stays hidden until you do.

* Only enabled projects appear in Auri PMS: the Project Hub, Portfolio, the Project field of every Auri PMS document and report, and the client status report schedule. Ordinary ERPNext projects are left alone.
* An Identifier is required to enable it. Ticking the box selects every active Ticket Type for the project; untick the ones you do not want.
* It cannot be switched off while the project has work items, releases, risks, sprints or time entries.
* Projects that already had an Identifier are enabled automatically by the upgrade.

**Client Status Report** - who gets the report and when.

| Field | What it does |
|---|---|
| **Report Recipients** | Email addresses (comma or new line) that receive the status report. Several people can be listed, for example the client contact and your manager. |
| **Send Weekly On** | The weekday the weekly report is emailed automatically; it covers the previous 7 days. Leave it blank for no weekly report. |
| **Send Monthly On Day** | The day of the month (1-28) the monthly report is emailed automatically; it covers the previous calendar month. Leave it blank for no monthly report. |

Use either one or **both**: a project can get a weekly and a monthly report. With both blank, reports are sent manually only, from the *Client Status Report* screen. A daily job does the sending, once per project per report period.

Every report that is sent is logged as a **Project Status Report**, so you can see what went out and when.

**Health Status** - where the project's health verdict is shown. The verdict is the traffic light (**On Track / At Risk / Off Track**), the 0-100 score and the reasons behind it. Counts, charts, tickets and hours are always shown; only the verdict is optional. All three boxes are off by default, so a new project shows no health judgement until you choose to.

| Checkbox | When ticked, the health status appears on |
|---|---|
| **Show on Project Hub (Health Dashboard)** | the project's health dashboard (the banner at the top) |
| **Show on Portfolio** | the Portfolio dashboard (the banner and the project's status in the table) |
| **Show in Client Status Report (email, PDF)** | the Client Status Report screen, the emailed report and its PDF |

**How the health status is worked out.** The status is calculated live from the project's own data, using these checks (the percentages and days below are the defaults; change them in **PMS Settings > Risk & Health**):

| Check | At Risk (amber) | Off Track (red) |
|---|---|---|
| Overdue open tickets | more than 10% of open tickets | more than 25% |
| Active sprint | slightly behind the ideal burndown (over 10% of scope) | well behind (over 25%) |
| Effort | hours spent run ahead of the work completed (over 25 points) | hours spent exceed the estimate |
| Releases | at 80% or less and due within 7 days, or just past the due date | past the due date and under 80% done |
| Risk register | a *High* open risk, or an open risk past its mitigation date | a *Critical* open risk |
| Backlog | more tickets created than resolved over the last 4 weeks (1.5x or more) | - |

- **Status:** *On Track* when nothing is flagged, *At Risk* when at least one amber check fires, *Off Track* when at least one red check fires.
- **Score:** starts at 100, minus 10 for each amber reason and 25 for each red reason (never below 0).
- **Reasons:** every flagged check is listed in plain words (for example "12% of open tickets are overdue (3)"), so the banner always says why. A ticket waiting on the client is shown as an information line and does not change the status or score.
- **No data yet:** a project without tickets shows no status.

This lets you keep the verdict internal (tick Hub and Portfolio only) while the client report shows just the facts, or show it everywhere once the project is healthy.

### Client Status Report: layouts, sections and defaults

Open **Client Status Report** from the sidebar, choose a project and period, preview the report, then **Email report** or
**Download PDF**.

**Layouts.** With no template chosen the report uses the built-in layout. The ready-made Email Templates are **Summary**,
**Summary Dark**, **Corporate** and **Corporate Grey**. All of them draw every section, including Progress by module, Plan and Time recorded. Make your own by writing an Email Template and ticking **Enable for Auri PMS**
on it; only enabled templates appear in the pickers. Choose the default in **PMS Settings > Status Report**, or pick one for a single
send with the **Email Template** field (or **Built-in layout**) on the report page.

**Sections.** The sections are Progress by module, Waiting on client, Delivered, In progress, Coming up next, Additional tickets,
Risks and issues, Plan, Risk register mitigation and Time spent, plus the summary figures and tiles (New tickets, Completion, and a tile each for Delivered, Open, Overdue, Waiting on you and Hours, which can be hidden without hiding their section).

* **Defaults:** in **PMS Settings > Status Report** tick the sections to include and drag the rows of **Section Order** (an empty
  table keeps each layout's own order).
* **For one report:** the **Sections** button on the report page shows each section with a drag handle and a checkbox. Applying
  it changes the preview, the PDF and the emailed report; it is cleared when you change the project or period.
* Scheduled (weekly and monthly) reports use the PMS Settings defaults.
* Switching a section off also removes its summary figure and the status reasons that belong to it.

**Tickets.** Every ticket of a section is listed. In **Tickets in this report** on the right you can remove a ticket from the
current send (x), or tick several tickets (a checkbox on each ticket, one per section, and *Select all*) and use **Remove selected** to take them all out at once after a confirmation; **Restore** brings one back. A pencil in front of each ticket adds a note for the client (up to 500 characters) that is shown under the ticket in the report, for this send only. You can also add any ticket of the project with an optional note for the client (it appears under *Additional tickets*).
Tick **Hide from Client Report** on a ticket to keep it out of every report and out of the client's health status.

**Email defaults.** **Default Recipients** are added to each project's own recipients (dialog and scheduled sends); **Default Subject**
is used when the chosen template has no subject (`{project}`, `{from_date}`, `{to_date}`).

**Attachments.** The email dialog has an **Additional attachments** list with **Add files** (up to 10 files, counted in the 10 MB limit). Only files uploaded there by the sender are accepted; they are attached to the email and to the *Status Reports Sent* record.

**Delivery.** Each sent report is a **Project Status Report** with *Emails Triggered*, *Delivered*, *Failed*, *Delivery Status*
(Queued, Sent, Partially Sent, Failed) and the error; the status is refreshed from the Email Queue. A report over 10 MB is refused
before sending; use **Download PDF** for very large reports.

**PDF.** The PDF fills an A4 sheet edge to edge with the report's own colour on every page. For Calibri text in the PDF install the
Carlito font on the server (`fonts-crosextra-carlito`).

Roles: **Auri PMS Admin** (and System Manager) see and administer everything, including the Portfolio of all projects; **Auri PMS Manager**
and **Auri PMS User** see only the projects they are a member of, plus public projects (a manager's Portfolio lists the projects they can
manage members for). Inside a project the member's **Project Role**
decides what they can do.

## 10-minute quick start

The app opens on the **Project Hub** (there is no home screen; the sidebar and the *Auri PMS* app icon start there). It lists the projects you are a member of (plus public ones). Open a project to see its tickets, overdue and unassigned counts, the active sprint with burndown, releases, team and time, and to create tickets, sprints and releases already scoped to that project. Views (list, board, Gantt, calendar) and reports open filtered to the project.

Dashboards (all share one theme choice, 8 themes in light and dark, and the *Range* menu: 1 month, 3 months, 6 months, Overall):

| Screen | For | What it shows |
|---|---|---|
| **Project Hub > Health Dashboard** | project manager, client | On Track / At Risk / Off Track with reasons, open vs closed, created vs resolved, backlog trend, sprint velocity, ticket aging, Billing graph, billable vs non-billable tickets, time by ticket category, team load and burnout risk, project notes, a final tickets and billable time by period table, tickets waiting on the client; every count opens its tickets |
| **Portfolio** | management | a status banner like the other dashboards (worst health, average score and the projects that need attention, for projects with the Portfolio switch ticked) and one row per project: health, open, overdue %, done %, budget burn, billable %, tickets waiting on the client; ticket, budget, flow and hour charts; project focus with Apply, trends by project, Billing graph, billable tickets, category treemap, team capacity, a tickets and billable time by period table and project notes; every count is clickable |
| **My Work** | everyone | my tickets by due date (overdue / today / this week / later), blocked and client-waiting badges, my sprints, hours this week against the weekly capacity, one-click *Log time*, a greeting, rings and a focus list; every count opens its list |
| **Quality Dashboard** | QA, project manager | bugs opened vs fixed, critical bugs, time to fix by priority, reopen rate, defects per 100 hours, bugs by category and project (ticket types marked *Counts as Defect*) |
| **Client Dependencies** (report) | project manager | every open ticket waiting on the client, how long, and what is needed; opened from the *Waiting on client* tiles |
| **Client Status Report** | project manager | a client-ready report for any period: status, delivered, in progress, coming up, risks, *Waiting on you*, plan and hours; email it (logged as *Project Status Report*), download a PDF, or let it go out weekly (Project > Auri PMS tab: *Report Recipients*, *Send Weekly On*) |

Tick **Dependent on Client** on a ticket (and say what you need): it records *Waiting since*, shows a banner on the ticket and is counted live in the hub, health dashboard, portfolio, My Work and the client report (where the ticket is listed under *Waiting on you*). Tickets waiting on the client are not counted as delivery delays in the project's status.

A daily scheduler job emails each assignee one digest of items that are due within the reminder window
or overdue.

## Development

```bash
bench --site <site> run-tests --app auri_pms          # whole suite
bench --site <site> run-tests --app auri_pms --module auri_pms.auri_pms.tests.test_workflow
ruff check . && ruff format --check .                      # Python
eslint --ext .js auri_pms                              # JS (default Frappe config)
```

Tests live in `auri_pms/auri_pms/tests/`, one file per area (304 tests at the time of writing); `utils.py` builds the shared fixture world once per class and isolates every test with a
database savepoint. Business rules live in the DocType controllers and `auri_pms/utils.py`; client
scripts are UX only.

Design decisions made where the specification was silent are listed in [DECISIONS.md](DECISIONS.md).

## Layout

```
auri_pms/
  hooks.py  install.py  permissions.py  patches/
  fixtures/                 custom fields, roles
  public/js/                auri_hub.bundle.js (shared dashboard UI and themes), auri_pms.bundle.js, project.js
  workspace_sidebar/  desktop_icon/
  auri_pms/
    utils.py                capabilities, hierarchy, roll-ups, progress formula
    api.py                  hub, health, portfolio, My Work and quality endpoints, log_time, link queries
    health.py  dashboards.py  status_report.py
    email_intake.py  tasks.py  project_hooks.py
    doctype/                Work Item, Sprint, Release, Time Entry, Ticket Type, Project Role, ...
    page/                   project_hub, portfolio, my_work, quality_dashboard, status_report
    report/                 work item, time log, release, sprint and client dependency reports
    tests/
```
