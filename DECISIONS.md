# Decisions

Choices made where the specification was silent, ambiguous or technically impossible as written.
Spec references are to *Auri PMS - Build Specification v1.0*.

## Permissions and visibility

1. **Visibility hooks only decide visibility.** `permission_query_conditions` / `has_permission`
   (`permissions.py`) hide records the user may not see. They deliberately return `True` for the
   `create` permission type, so capability errors keep the exact messages of the spec
   (R-04 "You are not allowed to create work items...", R-34, R-39) instead of a generic
   `PermissionError`.
2. **Frappe treats a `None` return from `has_permission` as "deny".** All hooks return explicit booleans.
3. **Project visibility is not narrowed for ERPNext project roles.** The membership/public filter on
   `Project` is skipped for Tracker/System Managers and for anyone holding the ERPNext roles *Projects
   Manager* or *Projects User*, otherwise installing the app would hide ordinary ERPNext projects from
   those users. Work Items, Releases, Time Entries and Categories are always filtered.
4. **Capability lookup is the single source of truth.** `auri_pms/utils.get_capabilities()` is used for
   every capability decision. The other places that read *Project Member* are not capability decisions: the SQL
   sub-query that builds the visibility filter, the assignee link query (lists candidates), the release-closed
   notification (lists recipients) and the Project hooks (validate the document's own rows).
   `get_capabilities(..., members_only=True)` skips the manager shortcut and the public-project fallback; it is
   used for R-11 (an assignee must be a real member) and for the ToDo check below.
5. **Delete permission on Work Item and Time Entry is granted to Auri PMS User at DocType level**
   (the matrix lists Create/Read/Write/Report). Frappe permissions can only be *granted* by role, and the
   spec's own tests need a Project Manager (a Auri PMS User) to delete items (T-118). The capability is
   enforced in `on_trash` (R-37 / R-39).
6. **Extra DocType permissions.** *Release*: Auri PMS User also gets `report` (the Release Progress report
   cannot run without it). *Work Item Category* and *Release*: Auri PMS User gets create/write, gated by
   `can_manage_categories` / `can_manage_releases` in the controllers.
7. **ERPNext DocTypes are opened with Custom DocPerms**, created idempotently in `after_install` and
   `after_migrate` (never by editing ERPNext files):
   * *Project*: Auri PMS Manager and System Manager read/write/create/report (System Manager "inherits Auri PMS Manager
     rights", but ERPNext's Project never listed it); Auri PMS User read/write.
   * *Activity Type*: Auri PMS Manager and Auri PMS User read (needed to choose an activity when logging time).
   Auri PMS User write on Project exists so that a project's own Manager can change members (section 4). A pure
   Auri PMS User (no ERPNext project role) may only change the Tracker tab; any other editable field change is
   rejected in `project_hooks`.
8. **Disabled users** get all-False capabilities and a `1=0` visibility filter immediately.
9. **System Manager and Administrator count as managers** (`utils.is_manager`) for every "Manager bypass".

## Naming, identifiers, Project fields

10. **Frappe's `set_only_once` rejects first-time values too**, which would block setting an identifier on a
    project that existed before install. R-02 "set once" is therefore implemented in the Project hook
    (changing or clearing a stored identifier fails with Frappe's standard "Value cannot be changed" text).
    `Work Item.project` and `Release.project` use the standard `set_only_once`.
11. **The identifier is mandatory in the UI only** (`mandatory_depends_on: eval:doc.__islocal`). A server-side
    requirement would break every ERPNext flow that creates Projects programmatically. R-03 is the server guard.
12. **Series numbers are not burned by rejected items.** R-03/R-04 are checked in `before_insert`, which runs
    before the name is generated.
13. **Release name needs the identifier before naming**, so `Release.before_insert` copies it.

## Work item rules

14. **Depth numbering:** a root item is level 1; with `max_subtask_depth = 5` the sixth level is rejected. When an
    item with subtasks is re-parented its own subtree height counts.
15. **Roll-up weights:** R-32 weights a parent's children by each child's `total_estimated_hours` (equal to
    `estimated_hours` for leaf items) so nested hierarchies weigh correctly.
16. **Release counts:** `total_items`, `closed_items`, `estimated_hours`, `spent_hours` cover all items of the release
    (own hours, so subtasks are not double counted); `percent_complete` uses only trackers with `show_in_roadmap`.
17. **R-21 and R-22 have no manager bypass** (the spec lists the bypass only on the rules that name it).
18. **R-24 reverse rows** are inserted/deleted directly and bump the related item's `modified`, so a stale form
    cannot silently overwrite the reciprocal row. `related_subject`/`related_status` of rows pointing at an item are
    refreshed when its subject or status changes.
19. **After `on_update` the in-memory document is refreshed** (`modified` and the roll-up fields) because Assign To
    bumps `modified` in the database; otherwise a second `save()` on the same object fails with a timestamp mismatch.
20. **Assignment:** `frappe.desk.form.assign_to` is used for the ToDo (status *Closed* when reassigned or on
    delete). A `ToDo.validate` hook applies R-11 to assignments made with the standard Assign To dialog.
    Document Follow rows are written directly because `follow_document` depends on a per-user setting.
21. **R-15** applies to every save of an existing item, including Kanban drags and status buttons.
22. **`get_allowed_statuses(work_item, doc=None)`** excludes the current status and inactive statuses; for an
    unsaved item it returns the open active statuses. `status_query` adds the current status for the form.

## Time entries

23. **R-39** requires `can_log_time` for the session user, and `can_edit_others_time` whenever the entry's user
    (current or previous) is somebody else. The lock (R-43) checks both the new and the original date.
24. `TE-.YYYY.-.#####` is used as the document naming rule.

## Notifications and email

25. **N-1** uses the standard Assign To notification (Notification Log + email according to the assignee's
    Notification Settings); it is skipped by Frappe for self-assignment. **N-2** (author and assignee, never the
    actor), **N-4** (daily digest) and **N-5** (release closed, all members, Notification Log) are Python because a
    Notification condition cannot exclude the actor per recipient or address project members. No Notification fixture
    is shipped; the `Notification` fixture filter (module Auri PMS) is registered so one can be added without code
    changes.
26. **`frappe.sendmail` has no `enqueue_after_commit` argument in v16.** Emails are written to the Email Queue inside
    the transaction (sent by the queue after commit). One email per recipient is queued; `queue_separately=True` sends
    immediately and commits, so it is not used.
27. **Email failures never block work.** `safe_sendmail` swallows and logs errors (for example no outgoing account)
    and also drops the popup message Frappe queues for that error.
28. **Email intake (R-40):** the tracker comes from the account, else *Support*, else the first active tracker.
    The created item skips R-04 (the sender is not the session user) but every other rule applies; failures are
    logged and never break mail download. A `[ID]` reply is attached only on mapped accounts.

## UI and packaging

29. **Workspace, Number Cards, Dashboard Charts and the four Script Reports are standard module documents**
    (loaded on install and every migrate) rather than exported fixtures; a Workspace Sidebar and a Desktop Icon are
    added because Frappe v16 needs them for the app to show on the desk. There is no *Gantt* option in a Workspace
    shortcut, so the Gantt shortcut is a URL shortcut (`/app/work-item/view/gantt`).
30. **The custom Quick Entry lives in `public/js/auri_pms.bundle.js`** (loaded on every desk page,
    built by `bench build`). Frappe only runs `work_item.js` when a form is opened, so a quick entry started from
    the list would otherwise use the default dialog.
31. **Status colours** are stored as hex; the list/form indicator name is computed on the server
    (`utils.nearest_indicator`, `api.get_status_indicators`).
32. **Default list filter** uses Frappe's `listview_settings.filters` (applied only when the user has no saved filters),
    for plain Auri PMS Users only.
33. **Work Item Summary** has two optional filters, *Closed From/To* (default last 30 days), to define "Closed in
    Period"; the spec lists none.
34. **Column order in the Time Entry list** follows the form field order (work item first); the spec's order
    (date first) can be set per user in List View Settings.
35. `tracker_default_tracker` and `tracker_project` live in their own *Auri PMS* section of Email Account.
36. **Default data** that Frappe would validate before `after_install` runs (PMS Settings link defaults) is set in
    `after_install`, not as field defaults.

## Testing

37. **Tests run on the real site.** No MariaDB root access was available for a separate test site. Each class builds
    the fixture world once and every test runs inside a database savepoint that is rolled back, so nothing is left in
    the database (verified after each run). Anything that commits (for example the Email Queue sender) would break
    that isolation, which is why emails are queued per recipient. Tests also cope with existing data on the site.
38. **Frappe skips Version rows in tests** unless `ignore_version=False`; the test helper saves with it so the
    history checks (UAT-04, T-076) are real.
39. **92 spec tests + `test_e2e.py` + 78 additional tests (22 sprints, 6 hub, 18 health, 6 portfolio, 10 my work, 13 quality, 14 status report, 10 client dependency)** (UI API, global search, performance and indexes, lifecycle,
    the missing outgoing mail account, ERPNext permissions): 210 in total.
40. **UAT-01..08** are scripted in `test_e2e.py`. UAT-09..14 are covered by automated tests (T-050/T-064, T-119,
    T-084, T-096/T-097, T-120..T-125) and the Desk was exercised with a headless browser for the workspace, list,
    quick entry, form buttons, Log Time, Close/Reopen, Kanban, Gantt, Calendar, the four reports, the Project Tracker
    tab and the outsider's view; a consultant should still run the 14 scenarios by hand before go-live.

## Sprints

42. **One project per sprint; a sprint is separate from a Release** (a release can span several sprints). A ticket has
    one Release and one Sprint field.
43. **Rules:** end date not before start date; sprints of a project may not overlap; lifecycle Planned -> Active ->
    Completed (no skipping, no going back); one Active sprint per project; Completed sprints keep their dates and
    goal; a ticket joins a sprint of its own project and only Planned/Active sprints accept tickets (existing members
    stay). Creating, editing and deleting sprints needs `can_manage_releases` (no new capability flag).
44. **Completing a sprint** moves unfinished tickets to the chosen Planned/Active sprint, or back to the backlog when
    none is chosen. The completed sprint therefore keeps only finished work, which is its velocity.
45. **Burndown** measures the tickets currently in the sprint in estimated hours (item count when nothing is
    estimated); a ticket burns on the day it was closed. Scope changes during the sprint are not replayed. The chart
    stops at today because Frappe draws missing values as zero; the table lists every day.
46. **Parent and child tickets** may sit in different sprints; each counts on its own.
47. **Bulk planning:** `move_to_sprint` saves every ticket through the normal rules; a failing ticket is rolled back
    alone and reported in the result. The Sprint Board button uses a URL filter because the Kanban view ignores route
    options.
48. **Standard files:** `delete_doc` in developer mode deletes a standard document's JSON file, so uninstall removes the
    Workspace, Workspace Sidebar and Desktop Icon rows with `frappe.db.delete` only.

## Project Hub

49. **Project-first entry point:** a standard Desk Page (`project-hub`) lists the projects the user can see and opens a
    per-project page. Data comes from two whitelisted calls (`get_hub_projects`, `get_project_hub`) that use
    `frappe.get_list`, so every visibility rule applies; the page also receives the user's capabilities and only offers
    the actions they may perform. Projects without an identifier are listed with a warning and open the Project form.
50. **Scoping:** list, Gantt, calendar, Kanban and report shortcuts pass `project` as a filter (Kanban/Gantt/calendar through
    the URL query, because those views ignore route options). The header of Frappe v16 pages shows breadcrumbs only, so the
    project name is rendered in the page body.

51. **Hub themes:** eight themes, each with a light and a dark palette that follows Frappe's own light/dark switch: *Glass + Soft*,
    *Soft UI (Neumorphism)* and four effect variants of it (*Convex*, *Pressed*, *Glow*, *Pearl*), *Minimal Clean* and *Flat - Solid
    colour* (no shadows or gradients). The earlier Flat Tinted, Flat Outline and Bento themes were removed. The choice is stored
    in the browser (`localStorage`), per user and device; a stored name that no longer exists falls back to Glass + Soft. Themes
    apply to the Project Hub and the dashboards only; no global stylesheet is loaded, so every other Desk screen keeps Frappe's stock look.

## Project Health dashboard and billable time

52. **Billable flag:** Time Entry gets `is_billable` (default on, so existing entries stay billable). It feeds the health
    dashboard, the *Time Log Summary* report (filter and two extra columns) and the Log Time dialog. No rates or invoicing
    are involved; billing from time stays out of scope.
53. **Definitions:** *created* = ticket creation date, *resolved* = date of `closed_on` of tickets that are currently closed
    (a reopened ticket stops counting). *Open backlog* at a period end = tickets created by then and not yet closed.
    *Resolution time* = creation to `closed_on`. *Burn* = spent hours / sum of ticket estimates. **Range:** 1 month (5 weekly
    buckets), 3 months (13), 6 months (26) or Overall (from the project's first ticket, time entry or sprint). Buckets are
    weeks starting on Monday; Overall switches to calendar months once the project is older than 26 weeks (at most 36
    months). The range only changes the charted series; open/closed totals, hours, status and velocity always describe the
    whole project. The "backlog grew" rule always looks at the last 28 days. The choice is stored in the browser.
54. **Health status** (traffic light plus a 0-100 score, 25 points per red reason and 10 per amber): overdue share of open
    tickets (>10% amber, >25% red); active sprint behind the ideal burndown (>10% amber, >25% red); spent hours over the
    estimate (red) or effort used 25 points ahead of work completed (amber); an open release past due and under 80% (red) or
    close to / just past due (amber); more than 1.5x as many tickets created as resolved over the last 4 weeks (amber).
    The reasons are listed next to the status so a client can see why.
55. *(removed)* A client-view toggle and a print button were tried and removed at the owner's request; the people-level
    panels (tickets and hours by person) always show.
56. **Sample data:** the Auriga sample tickets were back-dated (creation and closing dates spread over the project timeline) and
    meetings/support time marked non-billable so the dashboard has a history to show.

## Dashboards, client dependency and navigation

57. **No home screen.** The old Tracker workspace (number cards and charts) was removed with a patch; its content now lives in
    My Work (personal numbers) and the Portfolio (overview). The sidebar starts with the Project Hub and the app icon is
    called *Tracker*, so searching "tracker" in the Awesome Bar lists *Open Tracker* first and Enter opens the Project Hub
    (*PMS*, *Auri PMS* and *Open Project Hub* commands are also registered).
57a. **Tracker is now called Ticket Type.** The DocType *Tracker* (Bug, Feature, Task, Support) was renamed to *Ticket Type*, its
    children to *Ticket Type Transition* and *Project Ticket Type*; labels, messages and the sidebar follow. The specification
    calls it Tracker, so field names stay (`tracker` on Work Item and Project Ticket Type, `enabled_trackers`,
    `tracker_identifier`, `tracker_members`) to avoid renaming database columns; only DocType names and visible labels
    changed. The roles *Tracker Manager* / *Tracker User* are unchanged; the settings DocType is now *PMS Settings* (was *Tracker Settings*) and the app is called *Auri PMS* (was *Tracker*). A
    pre-sync patch renames the DocTypes on existing sites (data, Link fields and custom-field options follow).
58. **Shared UI kit.** Themes, styles and helpers live in `auri_hub.bundle.js`, loaded on demand by the five dashboard pages
    (Project Hub, Portfolio, My Work, Quality, Status Report). One saved theme and one saved range apply to all of them.
    ERPNext/Frappe screens and the app's own forms and lists keep the standard look (a global skin was tried and removed).
59. **Portfolio** covers projects with an identifier that the user can see (at most 200), computed with the same functions as the
    project health dashboard, so numbers agree. Sorted red first, weakest score first within a level.
60. **My Work** counts only open tickets assigned to the user; weekly capacity comes from PMS Settings (default 40 h). A
    ticket is *blocked* when it has a "Blocked by" relation to an open ticket.
61. **Quality** treats ticket types with *Counts as Defect* as bugs (the shipped Bug tracker is flagged by a patch). A bug is
    *reopened* when its status moved from a closed to an open status in Frappe's change history; reopen rate = reopened bugs /
    bugs ever closed. Defect density = bugs opened in the range per 100 hours logged in the range. Status: critical (Urgent or
    Immediate) bug open more than a week = red, any critical bug = amber, reopen rate >15% amber / >30% red (from 5 closed
    bugs), more bugs opened than fixed over 4 weeks = amber, >5 bugs per 100 hours = amber.
62. **Client status report.** One email-safe HTML (inline styles, every value escaped) feeds the preview, the email and the PDF
    (wkhtmltopdf). Sending needs `can_manage_releases`, checks that an outgoing Email Account exists first (Frappe would
    otherwise queue silently), and writes a *Project Status Report* log with the exact HTML. The weekly job runs daily, sends
    for projects whose weekday matches (covering the previous 7 days) and at most once a day per project.
63. **Dependent on Client.** `dependent_on_client`, `client_dependency_note` and `client_dependency_since` (stamped on ticking,
    cleared with the note on unticking). Counts are derived live from the checkbox, so they cannot drift. Only open tickets
    count. Overdue tickets that wait on the client are excluded from the delivery "overdue" rule and from the report's overdue
    list; the status gets an informational reason (shown, but it changes neither the level nor the score).

64. **Client-dependent split everywhere.** Every place that shows backlog, open/in-progress, created vs closed or an ageing
    profile (Project Hub overview and health, Portfolio, Quality, My Work) separates tickets *with us* from tickets *waiting on
    the client*, with a "Waiting on client" panel listing what is needed and for how long. The **Client Dependencies** script
    report (Project, Assigned To, Waiting since, days, note) is the drill-down; the Waiting on client tiles open it.

65. **Health status switches.** Project has three checkboxes, off by default (tick them to show the verdict): *Show on Project Hub (Health Dashboard)*, *Show on
    Portfolio* and *Show in Client Status Report*. Off hides only the verdict (level, score, reasons): the Health dashboard drops
    its banner, the Portfolio row reads "Hidden" (level none, counted under "No data"), and the report/email/PDF omit the status
    block. Counts, charts and hours are unchanged. The Quality and My Work dashboards have no project health verdict.

66. **Project Module and the Module field.** Work Item has a *Module* link to *Project Module*, a per-project master like Work Item
    Category (maintained with the *can_manage_categories* capability; the module must belong to the ticket's project). The field is
    named `project_module` in the database. Modules appear as "Open by module" on the hub overview, "Open vs closed (by module)" on
    Project Health, "Bugs by module" on Quality, a Module column on Client Dependencies and My Work, a Module filter on Work Item
    Summary, and "Progress by module" plus a small module line under every ticket in the client report. Tickets without a module are
    grouped as "(no module)" and the module tables are left out when nothing is tagged.
67. **Risk Register.** One *Risk Register* document per risk (name `<identifier>-RISK-0001`). Probability and impact are 1-5 scales;
    *Risk Score* = probability x impact and *Risk Level* is Low 1-4, Medium 5-9, High 10-14, Critical 15-25. Open means Identified,
    Mitigating or Monitoring; *Occurred* and *Closed* are not open. Anyone who can create tickets in the project (*can_create_items*)
    raises and edits risks, deleting needs *can_manage_releases*. Open risks feed the project health status: a critical open risk is a
    red reason, a high one an amber reason, and risks past their mitigation date add an amber reason (so the Portfolio banner and the
    client report carry them too). The client report lists only risks ticked *Show in Client Status Report*, with the mitigation plan
    as plain text. Visibility follows the project like every other document.

68. **Additional Assignees.** A child table (*Work Item Assignee*) next to *Assigned To*, which stays the single main assignee. Each extra
    person follows R-11 (enabled member, role with *can_be_assigned*), gets a ToDo and may edit the ticket like the assignee. Frappe's Assign To
    sets or clears the *Assigned To* field to the last person it touched, so after changing the table the controller writes the real value back.
    My Work and the due digest include the extra assignees; the team dashboards, health and reports still count the main assignee only.
69. **Project custom fields.** *Number of Custom Fields* (1-10) on the Project shows that many text fields. Every ticket carries a copy
    (*project_custom_n*, with the count) so they work as list columns and filters. A new ticket starts with the project's values; a value typed
    on the ticket is kept. A changed project value is passed on by a background job that saves each ticket (validation and versions apply)
    and only to tickets still holding the old value; lowering the count clears the extra values.
70. **Rule relaxations are PMS Settings switches, off by default.** *Keep Closed On Visible and Editable*, *Allow Completed Sprint for Closed
    Tickets* and *Allow Reopening a Completed Sprint* each loosen one rule and nothing else: a Closed On typed while closing is kept (otherwise
    stamped), a closed ticket may sit in a Completed sprint (open tickets may not), and a Completed sprint may return to Active (never to
    Planned, and never beside another Active sprint; tickets carried over earlier stay where they are).
71. **Status report attachments.** Extra files come only from the sender's own fresh uploads: the file must be owned by the sender and attached
    to no document, so the dialog cannot be used to email someone else's file. At most 10 files, counted in the 10 MB limit; they are then
    attached to the *Project Status Report* record. BCC was removed from the report; the CC field and recipients remain.
72. **Never overwrite.** Patches and fixtures only create or fill what is missing or still equals the previous shipped value (stored Email
    Templates and PMS Settings values chosen by people are kept); stored data changes go through document saves, not raw SQL.
73. **Install never deletes a Custom Field.** The *Enable for Auri PMS* field on Email Template is saved with `ignore_validate`, as fixture
    import does, so Frappe does not re-check every Email Template field. A site restored from an older Frappe can hold a Custom Field that
    duplicates a core field (`reference_doctype`); that used to stop `install-app`. The duplicate is left alone; removing it is the site
    owner's step in Customize Form.
74. **Members See All Work Items.** A PMS Settings switch, ticked by default. Unticked, the Work Item visibility rule (the permission query and
    `has_permission`) limits a *member* whose Project Role cannot manage members to the tickets assigned to them or raised by them (*Author*), in their projects only;
    managers, admins and non-members of a public project are unchanged. Insights reads Work Items with raw SQL, so it applies the same
    condition. A Check on a Single that was never saved reads as 0, so the stored row is read: no row means ticked.
75. **Delivery & Health.** A new page with the Portfolio's access rule (Auri PMS Admins, and the managers of a project for their projects),
    covering projects with Auri PMS switched on. Definitions: *delayed project* = Open with an overdue release, sprint or task; *overdue
    release* = not Closed with a due date in the past; *overdue sprint* = not Completed with an end date in the past; *completed task* = closed
    and not Rejected. A Release has only a due date, so its actual date is the day its last ticket was closed (no new fields); a Sprint has no
    release link, so it is listed under the releases of its tickets. Data is read with `get_list`, so the visibility rules, including *Members
    See All Work Items*, apply. Its Project, Release and Sprint filters are project-wise like the rest of the app: a release or sprint
    must belong to the chosen project (the server refuses a mismatch), the dropdowns offer only what was created for that project, and a
    release keeps the sprints that hold its tickets and the other way round. The *Sprint Burndown* report got the same Project filter.

76. **Portfolio merged into Delivery & Health.** Both pages had the same audience (`portfolio_projects`) and repeated project, open,
    overdue, closed and waiting-on-client numbers. The Portfolio class moved unchanged into `auri_portfolio.bundle.js` and the Management
    Dashboard shows it as a second tab (Delivery | Health and cost); the Project filter focuses it, Release and Sprint do not apply to it.
    `get_portfolio` and its tests stay, so nothing about the numbers changed. The `portfolio` Page remains as a redirect (`?tab=health`) so old
    links and bookmarks keep working; only its sidebar item was removed.

77. **The client reads a plain status.** The internal status (Off Track, score, percentages, release codes) is for the team. The report
    shows `client_status`: a heading by level and one fixed sentence per area (plan, issues, time, risks, backlog), and the tickets that
    wait on the client are counted but listed only in their own section. Nothing about how the level is worked out changed. The four
    ready-made Email Templates already saved on a site keep their wording until *Update* is run on them; the built-in layout changed.

78. **Auri Insights covers allocated projects.** Insights reads with raw SQL across projects, so its scope is stated once, in
    `get_insight_projects`: the Auri PMS projects the user is a member of, or every one for an admin (`is_allocated`). Reading a public
    project elsewhere is unchanged; it simply is not part of a person's analysis. The Work Item condition (*Members See All Work Items*) still applies on top.

## Uninstall

41. Custom Fields, the Kanban board, workspace, sidebar, icon and the Custom DocPerms the app added are removed.
    Frappe keeps the *database columns* of deleted custom fields (so identifiers survive a re-install), and the
    ERPNext Project / Activity Type keep the Custom DocPerm copies that mirror their standard permissions.

## Known limitations and v2 ideas

* Wiki, news, forums, Git browser, per-project custom fields, billing from time and a client portal are out of scope;
  Time Entry has no link to ERPNext Timesheet (a Timesheet billing sync is a natural v2).
* Notification templates are code, not editable Notification documents.
* No bulk "move items between releases" action; no email threading beyond the `[ID]` subject tag.
* The status colour and default % done of a status are not re-applied to existing items when changed.

- **Roles renamed (24 Oct 2026).** *Tracker User* / *Tracker Manager* are now *Auri PMS User* / *Auri PMS Manager* to match the app name. Behaviour is unchanged. The `rename_tracker_roles` patch renames the roles on existing sites, so people, DocType permissions and the app icon keep their access.

## Allocation decides who can change a project

* **Public means read-only.** A public project is visible to everyone, but `get_capabilities` gives a non-member no capability at
  all, so they cannot create, edit, delete or log time. The PMS Settings *public project role* no longer grants anything.
* **Changing a record needs allocation.** `has_permission` refuses write, delete, submit, cancel and amend on any project-bound
  document (and on a PMS-enabled Project) unless `is_allocated(project, user)`: a member of the project, an Auri PMS Admin or a
  System Manager. An ERPNext Projects role does not change that.
