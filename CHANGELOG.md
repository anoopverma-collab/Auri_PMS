# Changelog

All notable changes to Auri PMS are listed here, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
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
- The Auri PMS sidebar is shown on pages that take a project in their address (Project Hub, Client Status Report), also after a
  refresh or from a direct link. The generated *Tracking* sidebar and the old *Tracker* name no longer appear in the top-left
  corner.
- Dark-mode readability of the Soft UI Convex and Pearl themes.
- Singular wording ("1 ticket is waiting on the client", "1 day").

## Earlier work

- Project Hub with project-first navigation, sprints, releases and Kanban, Gantt and calendar views.
- Project Health, Portfolio, My Work, Quality and Client Status Report dashboards with a shared theme and range.
- *Dependent on Client* tracking with counts on every dashboard and a Client Dependencies report.
- Time entries with billable hours, ticket types and workflow, and a per-project health switch for the hub, portfolio and report.
- Continuous integration (lint and the full test suite on a clean Frappe and ERPNext v16 site).
