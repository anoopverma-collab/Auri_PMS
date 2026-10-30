# Changelog

All notable changes to Auri PMS are listed here, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Members See All Work Items** (*PMS Settings > General > Ticket Rules*, ticked by default). Unticked, a project member sees only the Work Items assigned to them (*Assigned To* or *Additional Assignees*) instead of every ticket of their projects: in the list, search, links, the Project Hub, reports, Portfolio and Insights. Admins and members whose Project Role can manage members still see everything, and a public project stays readable for non-members. A site that never saved the setting keeps today's behaviour.
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
- **Insights:** a gallery of six ready-made analytical dashboards on Auri PMS data, in the style of the Power BI samples: *Delivery
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
