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
| **Tracker** | type of work item, default status, optional allowed-transition table per project role (empty = everything allowed) |
| **Project Role** | the nine capability flags (create/edit/delete items, manage releases/categories/members, log time, edit others' time, be assigned) |
| **Project > Tracker tab** | identifier (2-10 chars, set once), parent project, public flag, members + role, enabled trackers |
| **Email Account** | optional: *Tracker Project* (+ default tracker) turns received mail into work items |

Roles: **Tracker Manager** (and System Manager) administer everything; **Tracker User** sees only the
projects they are a member of, plus public projects. Inside a project the member's **Project Role**
decides what they can do.

## 10-minute quick start

1. Give yourself the *Tracker Manager* role. Open the **Tracker** workspace.
2. Open a Project (or create one), go to the **Tracker** tab, set an **Identifier** (e.g. `WEB`), add
   members with a project role (Manager / Developer / Reporter) and save. Members who lack a tracker
   role get *Tracker User* automatically.
3. Press **New Work Item** (quick entry): subject, project, tracker, priority, assignee, due date. The
   item is named `WEB-00001`; the assignee gets a ToDo and a notification, the assignee and author follow it.
4. Work it: the **Status** dropdown only offers valid next statuses; use **Log Time**, **Add Subtask**,
   **Close** / **Reopen**, relations (Blocks / Blocked by ...), comments and attachments.
5. Plan work into a **Release** (Releases list); progress is computed automatically.
6. Use the views: List (default filter: open items), **Kanban** (Work Items by Status), **Gantt** and
   Calendar, plus the reports *Work Item Summary*, *Time Log Summary*, *Release Progress* and
   *Overdue Work Items*.
7. Optional: set *Tracker Project* on an incoming Email Account; each received mail becomes a work
   item, and replies containing `[WEB-00001]` in the subject are attached to that item.

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
