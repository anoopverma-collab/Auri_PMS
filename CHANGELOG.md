# Changelog

All notable changes to Auri PMS are listed here, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Monthly client status report:** a project can email its status report *Monthly* (on a chosen day, 1-28, covering the
  previous calendar month) as well as weekly; set it in the *Client Status Report* section of the Project's Auri PMS tab.
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
- Renamed the app to **Auri PMS (Project Management System)**; the Python package is now `auri_pms`.
- Dashboards use aligned layouts: columns end on the same line, project cards have equal height, the project overview and
  Project Health are built from rows of paired panels, and every screen shows 8 tiles in two rows of four.
- Soft UI theme variants (Convex, Pressed, Glow, Pearl) replace the earlier colour variants.
- The sidebar header shows *Auri PMS* with the tagline *Plan. Track. Deliver.*

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
