# Changelog

All notable changes to Auri PMS are listed here, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] - 2026-10-31

Tested with Frappe 16.54 and ERPNext 16.53.

### Added
- **Statuses per project.** *Project > Enabled Statuses* (new table on the Project) lists the Work Item statuses a project uses. The Status dropdown, the Close and Reopen buttons and the allowed next statuses offer only those; saving a status that is not enabled is refused. Switching Auri PMS on lists every active status as a start. With no project chosen the Status dropdown shows "Select a Project first".
- **Modules tagged per project.** *Project Module* is now a shared record, named by its module name, and each project has an *Enabled Modules* table. The Work Item Module dropdown offers only the project's modules and a module that is not enabled is refused. Project managers and Auri PMS Managers can create modules. A patch tags every existing module on the project it belonged to.
- **Field rules per Project Role.** *Project Role > Work Item Field Rules* lists every Work Item field with a *Can Edit* tick. A field that is unticked is view only for that role on an existing work item: refused on save (form, list, API) and read-only on the form. Developer and Reporter start with the subject, project, sprint, release and the four dates view only; Manager has none. The *Permissions* column of the role list shows the result.
- **Can See All Work Items, per Project Role.** A tick on the Project Role replaces the site-wide *Members See All Work Items* switch (removed). Unticked, that role sees only the items assigned to it (also as an additional assignee) or raised by it, project by project. A patch keeps today's behaviour: roles that can manage members stay ticked.
- **One rule for every New button.** The *Create rules* table in `utils.py` says which project capability each record needs (Work Item, Time Entry, Risk Register, Sprint, Release, Work Item Category, Project Module; Status Report and Snapshot are system-made). The server sends the answers at login and the New button, menu shortcuts and new forms follow them. Each record still checks the capability on its own project when it is saved.
- **Delivery & Health for every member.** The page, both tabs and the Portfolio now list the projects a person is a member of (all projects for an admin), whatever their Project Role. Project notes and the team workload stay with project managers.
- **Project dropdowns that work for members.** All Auri PMS Project dropdowns (the forms of Release, Sprint, Time Entry, Risk Register and Work Item Category, the reports, Insights, the Quality Dashboard, the Client Status Report and the Work Item calendar and list filters) use `project_link_query`. The setting *PMS Settings > Auri PMS Projects Ignore Company Restrictions* (ticked by default) keeps a Company User Permission from hiding a project the person is a member of on those screens; the standard Project list and form still follow the restriction.
- **Work Item form.** The Parent Work Item can come from the project or its parent project. Waiting Since is editable when *PMS Settings > Waiting Since Editable* is ticked. Hide from Client Report now sits before Dependent on Client. Project-bound dropdowns (Status, Ticket Type, Assignee, Category, Module, Release, Sprint, Parent) show "Select a Project first" once when no project is chosen and then offer nothing.
- **Time Entry form** is grouped into sections; Comment is required (also in the Log Time dialog); Employee and Release show only when set.
- **Project Role list** shows a *Permissions* summary of what each role allows.

- **Quality Dashboard.** The Project dropdown lists only projects with Auri PMS switched on. The data is now selected and counted in the database (only bug tickets come back as rows; created-in-period counts, first dates and hours are aggregates), so it is faster on large sites; the numbers are identical.
- **Delivery & Health: several projects at once.** The Project filter is now a multi-select ("Projects"): tick any number of projects and every block, the tiles and the hours chart cover exactly those. The list always offers every project you manage, Release and Sprint offer only what belongs to the ticked projects, and a release or sprint of a project you un-tick is cleared. The Health and cost tab opens focused on the same projects. Tiles open lists of the ticked projects only.
- **Sidebar:** *Client Status Report* sits directly below *Delivery & Health*.
- **Health and cost: "Why this status" moved up.** It now sits directly under *Projects at a glance*, above *Trends by project*, so the reasons behind each score are next to the scores.
- **Client Status Report: wide preview.** The preview now stretches the report to the full width of its pane instead of leaving it as a narrow column; the layouts' own maximum width (640 to 720 px) still applies to the email and the PDF, so what the client receives is unchanged.
- **Delivery & Health: hours.** A new section *Hours: estimated vs actual vs billable* with a grouped bar chart and a table per project (estimated on the tickets, actual = time logged, billable = the billable part, billable share, and actual against the estimate). It is all time, follows the Project, Release and Sprint filters (a release or sprint keeps the time logged on its tickets) and has a total row.
- **Only Auri PMS projects, everywhere.** Every Project picker now offers projects with Auri PMS switched on: the Client Status Report page, the Work Item calendar filter and the Project Dashboard Snapshot form joined the pages, reports and forms that already did. The Quality Dashboard leaves out a project that was switched off after it got records and refuses it by name.
- **Auri Insights scope.** Insights now covers the Auri PMS projects the user is allocated to (every project for an admin) instead of every project they could read, so a public project they are not on is no longer in their analysis. The Project dropdown offers the same list, and asking for another project is refused. Reports for someone with no allocation are empty, not an error.
- **Delivery & Health tiles:** *Delayed projects*, *Delayed releases*, *Overdue sprints* and *Pending activities* now open the list of exactly the records they count; they were the only tiles in the app that were not clickable.
- **Sidebar:** the *Project Hub* and *Quality Dashboard* entries are removed from the Auri PMS sidebar. Both pages still work (links, buttons, `/desk/project-hub` and `/desk/quality-dashboard`); only the sidebar entry is gone. A site's saved sidebar arrangement keeps what it holds, so those two rows had to be removed there too.
- **Project Hub, Work tab:** the panel *Estimated vs spent hours* is now *Estimated vs spent vs billable hours* and ends with a line such as "Billable is 62% of the 40 h spent" (or "No hours logged yet").
- **Client Status Report: plain status for the client.** The status box in the email, PDF and preview now shows a heading ("On track", "On track, with a few items to watch" or "Needs attention") and one plain line per area (plan, overdue tickets, effort, risks, backlog), with no score, percentages or release codes. What waits on the client is only counted ("2 items need your input (see below)"); the full list stays in its own section. The sender's side panel still shows the score and reasons. Email Templates can use the new `client_status` variable (`label`, `level`, `points`); templates you edited keep working with `r.status`.
- **Portfolio merged into Delivery & Health.** The Portfolio is now the *Health and cost* tab of Delivery & Health (health score, budget burn, billing, risks, team capacity, trends and the period table, unchanged); the Project filter focuses it. The Portfolio sidebar entry is gone, and the old `portfolio` route and the Project Hub button open the new tab. The backend and its numbers did not change. Site-saved sidebar arrangements must drop the Portfolio row themselves.
- **Delivery & Health** (*Auri PMS > Delivery & Health*). One page for every Auri PMS project the user manages (same audience as the Portfolio): project overview (total, active, completed, delayed), task overview (total, open, in progress, completed, overdue), project-wise progress, release-wise tracking with planned and actual dates and completion, sprint overview with progress and overdue sprints, user-wise workload, and delivery health (upcoming deadlines, delayed releases, pending activities). A project counts as delayed when it is Open and has an overdue release, sprint or task. A release's actual date is derived from its last closed ticket, so no field was added. Project, Release and Sprint filters narrow every block; the Release and Sprint dropdowns list only what was created for the chosen project, and choosing another project clears them.
- **Members See All Work Items** (*PMS Settings > General > Ticket Rules*, ticked by default; later replaced by *Can See All Work Items* on the Project Role, see above). Unticked, a project member sees only the Work Items assigned to them (*Assigned To* or *Additional Assignees*) or raised by them (*Author*) instead of every ticket of their projects: in the list, search, links, the Project Hub, reports, Portfolio and Insights. Admins and members whose Project Role can manage members still see everything, and a public project stays readable for non-members. A site that never saved the setting keeps today's behaviour.
- **Select and remove several tickets from a client status report.** *Tickets in this report* has a checkbox on every ticket, one per section and *Select all*, with a *Remove selected (n)* button that asks for confirmation. *Restore* still brings a ticket back.
- **Custom fields on the Project, copied to tickets.** *Number of Custom Fields* (1-10) on the Project's Auri PMS tab shows that many text fields, *Custom 1* to *Custom 10*, three to a row. Tickets show the same number of fields (*Project Custom Fields* on the Work Item), filled from the project and editable on the ticket. A changed project value reaches the tickets that still hold the old one; a value typed on a ticket is kept. They can be list columns and filters. Lowering the number clears the extra values.
- **Keep Closed On visible and editable** (*PMS Settings > General > Ticket Rules*). When ticked, *Closed On* on a Work Item can be edited, and a date entered while closing a ticket is kept instead of being replaced by the closing time. Off by default.
- **Hide any summary tile on its own.** Delivered, Open, Overdue, Waiting on you and Hours tiles each have a switch (in the *Sections* dialog and in *PMS Settings > Status Report*), next to the existing New tickets and Completion switches, so a tile can be hidden while its section stays.
- **A note for the client under any ticket.** A pencil in front of every ticket in *Tickets in this report* opens a note box (500 characters); the note shows in italics under the ticket's subject in every section, in the preview, PDF and email, for that send only.
- **Summary and Summary Dark** email templates now draw *Plan*, *Progress by module* and *Time recorded*, so those sections show when ticked. A patch refreshes stored copies that were never edited.
- **Sprint settings** (*PMS Settings > General > Ticket Rules*, both off by default): *Allow Completed Sprint for Closed Tickets* lets a closed ticket be moved to a Completed sprint (the picker lists them too), and *Allow Reopening a Completed Sprint* adds a *Reopen Sprint* button that returns it to Active when no other sprint of the project is active.
- **Additional Assignees on a Work Item.** A table next to *Assigned To* for more people working on a ticket. Each must be a project member who can be assigned (like Assigned To), gets a ToDo, and sees the ticket in *My Work* (lists, tiles and the sprint count) and in the due-date digest. Assigned To stays the main assignee; the other dashboards and reports still count that person only.
- **Additional attachments on the emailed report.** The *Email status report* dialog has an *Additional attachments* list with an *Add files* button (up to 10 files, counted in the 10 MB limit). Only files uploaded in that dialog by the sender are accepted; they are attached to the email and then to the *Status Reports Sent* record.
- **CC on the Client Status Report.** The *Email status report* dialog has a CC field. A project can keep standing *Report CC*
  addresses, and PMS Settings has *Default CC* that is added to every project. They are used by the scheduled weekly and monthly
  reports too. An address already in To is not repeated, and *Status Reports Sent* records the To and CC lists.
- **Tickets on the Release and Sprint forms:** a *Tickets in this release / sprint* panel with the totals (tickets, closed, open, hours), a count per status
  and per person, and the list of tickets (owner, sprint, due, % done), plus a *View tickets* button and a Work Item connection.
- **Release and Sprint chips** on every ticket row in My Work.
- **Actual Start Date** and **Actual End Date** on Work Item, next to the planned Start and Due Date. The actual end cannot come before the actual start.
- **Project Health sub-tabs:** the long Health page is split into *Overview*, *Work*, *Time and billing*, *People* and *Plan*.
- **Auri Insights** (formerly *Insights*): a gallery of six ready-made analytical dashboards on Auri PMS data, in the style of the Power BI samples: *Delivery
  Analysis*, *Team Workload*, *Releases and Sprints*, *Quality Analysis*, *Client Dependency* and *Time and Billing*. Each has KPI
  cards, charts, breakdowns and a detail table, follows the project and range filters, and cards open the matching list.
- **Project page tabs and History:** every project now has one page with *Overview*, *Health* and *History* tabs and quick links to its
  tickets, releases, sprints, risks and time. *History* keeps the Project Health dashboard project by project: a **Project Dashboard
  Snapshot** is saved every Monday and on the 1st of each month (and with *Save snapshot*), with a trend chart, change since the last
  one and a read-only view of any past dashboard.
- **Delete a saved dashboard:** each row of *History* has a *Delete* link (with a confirmation) for a snapshot saved by mistake or with wrong data.
  Only people allocated to the project, or an admin, can delete.
- **Portfolio redesign:** Hub-style page with project focus (Apply button, other projects hidden until Show all), clickable counts,
  trends by project, Billing graph, billable vs non-billable tickets, time by ticket category (treemap), team capacity with
  over-allocation and burnout flags, a final *Tickets and billable time by period* table (Overall, 7 / 30 / 90 days, this
  year, custom range) and project notes (add and delete, also shown on the Project).
- **Project Health** takes the same billing, notes and period table for its one project, plus a *Team load and burnout risk*
  panel; the weekly billable chart became the Billing graph. API: `get_project_periods`; `get_project_health` adds `billing`,
  `notes`, `can_note`, `starts` and `team`.
- **My Work** redesign: time-of-day greeting, rings, a focus list, per-group *Open list* links and clickable counts.
- **Configurable risk and health thresholds** in PMS Settings (*Risk & Health* tab): the Medium, High and Critical score levels
  of the Risk Register, and every health check (overdue tickets, sprint burndown, effort, releases, backlog growth) with its
  score penalties. Existing sites get the previous values through patches.
- **Client Status Report: email templates.** Ready-made Email Templates (Summary, Summary Dark, Corporate, Corporate Grey) plus
  the built-in layout. A new *Enable for Auri PMS* checkbox on Email Template decides which templates the pickers list; the
  default template is chosen in PMS Settings and can be overridden for one send on the report page, with a *Built-in layout* switch.
- **Sections:** every section of the report can be switched on or off and moved. PMS Settings has the default switches and a
  drag-to-reorder *Section Order* table; the report page has a *Sections* dialog (checkbox, drag handle) for one report. Summary
  figures, the summary sentence, the status reasons and the ticket list all follow the chosen sections.
- **Tickets in a report:** remove tickets from one send, hide a ticket from every report (*Hide from Client Report* on the Work
  Item; client health ignores hidden tickets) and add any ticket with a note for the client in an *Additional tickets* section.
- **Email defaults** in PMS Settings: default recipients (added to each project's own) and a default subject with
  `{project}`, `{from_date}`, `{to_date}`.
- **Delivery tracking** on Project Status Report: emails triggered, delivered, failed, delivery status and error; the status is
  refreshed from the Email Queue. A report over 10 MB is refused before sending with a clear message.
- **PDF** of the report fills an A4 sheet edge to edge (no paper margin, one colour behind every page, 0.2 inch spacing).
- **Enable Auri PMS** checkbox on the Project. Only enabled projects show in the Project Hub, Portfolio, reports and the Project field of every Auri PMS document; enabling selects all active Ticket Types by default. A patch enables existing projects that have an Identifier.
- **Monthly client status report:** next to the weekly schedule a project can set *Send Monthly On Day* (1-28); the report covers
  the previous calendar month. Weekly and monthly can be used together.
- **Risk Register** DocType: probability x impact scoring (Low, Medium, High, Critical), owner, status, mitigation and
  contingency plan, mitigation due date, related ticket and a *Show in Client Status Report* switch. Risks are numbered per
  project (`AURI-RISK-0001`).
- Open risks feed the **project health status** (critical and high risks, overdue mitigations), so the Project Health banner, the
  Portfolio banner and the client report carry them.
- Risk panels: heat map and top risks on Project Health, a risk panel on the project overview, a *Risks* column and an *Open risks
  by project* panel on the Portfolio, *Risks I own* on My Work, and *Risks and mitigation* in the client report.
- **Module** field on tickets, backed by the new per-project **Project Module** DocType. Breakdowns by module on the project
  overview, Project Health and Quality, a Module column on My Work and Client Dependencies, a Module filter on Work Item Summary,
  and *Progress by module* in the client report.
- **PMS Settings** (renamed from Tracker Settings) with a migration for existing sites.
- App logo, social preview image and light and dark screenshots of every screen in the README.

### Changed
- **Hidden from project members:** Project Role, Work Item Status and Ticket Type (read removed from *Auri PMS User*; the dropdowns that need them have their own queries), the Project Module and Work Item Category lists (only people who may manage them see them), the Release *New* button, and Project Dashboard Snapshots (now scoped to the project like the other records).
- **Client Status Report:** the "not started" status is the default starting status of PMS Settings, ignoring inactive statuses.
- **Auri Insights reads tickets with `frappe.get_list`** instead of a hand-built SQL string, and picks its report from a fixed list instead of a name lookup. The numbers and the *Members See All Work Items* limit are unchanged (the Frappe Semgrep security rules flagged the old form).
- **Security scan.** The app now scans clean (0 findings) against the official `frappe/semgrep-rules`. The three intended cases carry a `# nosemgrep` with the reason beside it: the yes/no `has_permission` for the Delete button, and the `set_user` and `commit` calls in the developer-only `e2e/` scripts.
- **`e2e/dashboards.py` no longer starts another process.** Pass the output of `e2e/sessions.py` in the `SESSIONS` variable (the file header has the command).
- **CI:** `actions/checkout`, `actions/setup-python` and `actions/setup-node` are v7, and the lint job runs on `ubuntu-24.04` like the test job.
- **Editing needs allocation.** A user changes data only in projects they are allocated to (a member of the Project); an Auri PMS Admin
  or System Manager changes any project. A public project stays visible to everyone but is read-only for people who are not
  members, and an ERPNext Projects role no longer lets someone edit a PMS project they are not on.
- The status report lists **every ticket** of each section (the earlier per-section limits and "+ N more" lines are gone).
- Report layouts use the Calibri font (with Carlito, Segoe UI and Arial as fallbacks) and the footer reads *Sent through Auri PMS*.
- Corporate shows the summary figures in equal-width boxes, four to a row.
- The module is now called **Auri PMS** (was *Tracking*) and the Python package is `auri_pms.auri_pms`; a migration patch moves existing sites over.
- Renamed the app to **Auri PMS (Project Management System)**; the Python package is now `auri_pms`.
- Dashboards use aligned layouts: columns end on the same line, project cards have equal height, the project overview and
  Project Health are built from rows of paired panels, and every screen shows 8 tiles in two rows of four.
- Soft UI theme variants (Convex, Pressed, Glow, Pearl) replace the earlier colour variants.
- The sidebar header shows *Auri PMS*.

### Fixed
- **Project Dashboard Snapshot** was visible to users outside its project; it now follows the project rule.
- **Statuses, categories and modules no longer list everything** when no project is chosen.
- **Sprint Burndown** report: the Sprint dropdown listed the sprints of every project. It has a Project filter now and offers only that project's sprints; a sprint of another project is refused.
- The summary header and progress bar no longer appear twice on a new Sprint, Release or Work Item right after its first save.
- Project Hub: release labels on the timeline no longer overlap, and the Releases list on Project Health scrolls instead of stretching the page.
- The Auri PMS sidebar is shown on pages that take a project in their address (Project Hub, Client Status Report), also after a
  refresh or from a direct link. The generated *Tracking* sidebar and the old *Tracker* name no longer appear in the top-left
  corner.
- Dark-mode readability of the Soft UI Convex and Pearl themes.
- Singular wording ("1 ticket is waiting on the client", "1 day").
- `install-app` no longer stops with *Email Template: Fieldname reference_doctype appears multiple times* on a site restored from an older Frappe, where a leftover Custom Field duplicates a field Frappe now ships. The *Enable for Auri PMS* field is saved without re-checking every Email Template field (as fixture import does); nothing is removed from the site.
- CI: the Tests job runs on Ubuntu 24.04, because `ubuntu-latest` (26.04) has no `wkhtmltopdf` package.

## Earlier work

- Project Hub with project-first navigation, sprints, releases and Kanban, Gantt and calendar views.
- Project Health, Portfolio, My Work, Quality and Client Status Report dashboards with a shared theme and range.
- *Dependent on Client* tracking with counts on every dashboard and a Client Dependencies report.
- Time entries with billable hours, ticket types and workflow, and a per-project health switch for the hub, portfolio and report.
- Continuous integration (lint and the full test suite on a clean Frappe and ERPNext v16 site).
