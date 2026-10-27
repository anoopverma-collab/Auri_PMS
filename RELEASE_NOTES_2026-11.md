# Auri PMS: November 2026 Release

Release name: **Auri PMS November 2026 Release**
App: Auri PMS (Project Management System), `auri_pms`
Month: November 2026

## Features

### Dashboards
- **Portfolio redesign:** Hub-style page with project focus (Apply button, other projects hidden until Show all), clickable counts, trends by project, Billing graph, billable vs non-billable tickets, time by ticket category (treemap), team capacity with over-allocation and burnout flags, a *Tickets and billable time by period* table (Overall, 7 / 30 / 90 days, this year, custom range) and project notes.
- **Project Health** gets billing, notes and the period table for its one project, plus a *Team load and burnout risk* panel.
- **My Work** redesign: time-of-day greeting, rings, a focus list, per-group *Open list* links and clickable counts.
- **Configurable risk and health thresholds** in PMS Settings (*Risk & Health* tab). Existing sites get the previous values through patches.

### Client Status Report
- **Email templates:** ready-made templates (Summary, Summary Dark, Corporate, Corporate Grey) plus the built-in layout, all drawing every section (Summary and Summary Dark now include Plan, Progress by module and Time recorded); *Enable for Auri PMS* checkbox on Email Template; default chosen in PMS Settings and overridable per send.
- **Sections:** every report section can be switched on or off and reordered, in PMS Settings (defaults) and per report (*Sections* dialog).
- **Tickets in a report:** remove tickets from one send, hide a ticket from every report (*Hide from Client Report*), and add any ticket with a client note in *Additional tickets*.
- **Project custom fields:** pick 1-10 and that many *Custom* text fields appear on the Project; tickets carry a copy that can be shown as list columns.
- **Keep Closed On visible and editable:** a PMS Settings checkbox that lets people edit *Closed On* on a ticket and keeps a date entered while closing.
- **Hide any summary tile on its own:** a switch per tile in the Sections dialog and PMS Settings, independent of its section.
- **Note for the client under any ticket:** a pencil in front of each ticket adds a note that appears under the ticket in the report.
- **Additional attachments:** add up to 10 files to the emailed status report from the Email dialog; they are kept on the Status Reports Sent record.
- **Sprint settings:** optionally allow closed tickets in Completed sprints, and reopening a Completed sprint.
- **Additional Assignees:** assign one ticket to several people; each gets a ToDo and sees it in My Work.
- **Select and remove several tickets at once:** a checkbox on every ticket, one per section and *Select all*, with a *Remove selected* button that asks for confirmation.
- **Email defaults** in PMS Settings: default recipients and a default subject with `{project}`, `{from_date}`, `{to_date}`.
- **Delivery tracking** on Project Status Report: triggered, delivered, failed, delivery status and error, refreshed from the Email Queue. Reports over 10 MB are refused before sending.
- **PDF** fills an A4 sheet edge to edge.
- **Monthly client status report:** *Send Monthly On Day* (1-28), covering the previous calendar month; can be used together with weekly.
- Every ticket is now listed in each section (the earlier per-section limits are gone).

### Risk, Modules and Projects
- **Risk Register** DocType: probability x impact scoring, owner, status, mitigation and contingency plan, related ticket, *Show in Client Status Report* switch; numbered per project (`AURI-RISK-0001`).
- Open risks feed **project health status**; risk panels on Project Health, project overview, Portfolio, My Work and the client report.
- **Module** field on tickets, backed by the per-project **Project Module** DocType, with breakdowns across dashboards and reports.
- **Enable Auri PMS** checkbox on the Project: only enabled projects show in the hub, Portfolio, reports and Project fields.
- **PMS Settings** (renamed from Tracker Settings), with a migration.
- App logo, social preview image and light/dark screenshots in the README.

### Changes
- Module renamed to **Auri PMS** (was *Tracking*); app renamed to **Auri PMS (Project Management System)**; package is `auri_pms`. Migration patches move existing sites.
- Aligned dashboard layouts: equal-height project cards, paired panels, 8 tiles in two rows of four on every screen.
- Soft UI theme variants (Convex, Pressed, Glow, Pearl) replace the earlier colour variants.
- Report layouts use Calibri (Carlito, Segoe UI, Arial fallbacks); footer reads *Sent through Auri PMS*.
- Sidebar header shows *Auri PMS*.

## Bugs fixed
- **Project Hub: overlapping releases.** Release labels on the timeline overlapped when due dates were close (for example two releases on the same day). Labels now use four lanes, two above and two below the line, so none overlap.
- The Auri PMS sidebar now shows on pages that take a project in their address (Project Hub, Client Status Report), also after a refresh or from a direct link; the old *Tracking* and *Tracker* sidebars no longer appear.
- Dark-mode readability of the Soft UI Convex and Pearl themes.
- Singular wording ("1 ticket is waiting on the client", "1 day").
