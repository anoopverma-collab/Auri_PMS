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
4. **Capability lookup is the single source of truth.** `tracking/utils.get_capabilities()` is used for
   every capability decision. The other places that read *Project Member* are not capability decisions: the SQL
   sub-query that builds the visibility filter, the assignee link query (lists candidates), the release-closed
   notification (lists recipients) and the Project hooks (validate the document's own rows).
   `get_capabilities(..., members_only=True)` skips the manager shortcut and the public-project fallback; it is
   used for R-11 (an assignee must be a real member) and for the ToDo check below.
5. **Delete permission on Work Item and Time Entry is granted to Tracker User at DocType level**
   (the matrix lists Create/Read/Write/Report). Frappe permissions can only be *granted* by role, and the
   spec's own tests need a Project Manager (a Tracker User) to delete items (T-118). The capability is
   enforced in `on_trash` (R-37 / R-39).
6. **Extra DocType permissions.** *Release*: Tracker User also gets `report` (the Release Progress report
   cannot run without it). *Work Item Category* and *Release*: Tracker User gets create/write, gated by
   `can_manage_categories` / `can_manage_releases` in the controllers.
7. **ERPNext DocTypes are opened with Custom DocPerms**, created idempotently in `after_install` and
   `after_migrate` (never by editing ERPNext files):
   * *Project*: Tracker Manager and System Manager read/write/create/report (System Manager "inherits Tracker Manager
     rights", but ERPNext's Project never listed it); Tracker User read/write.
   * *Activity Type*: Tracker Manager and Tracker User read (needed to choose an activity when logging time).
   Tracker User write on Project exists so that a project's own Manager can change members (section 4). A pure
   Tracker User (no ERPNext project role) may only change the Tracker tab; any other editable field change is
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
    is shipped; the `Notification` fixture filter (module Tracking) is registered so one can be added without code
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
30. **The custom Quick Entry lives in `public/js/auriga_track.bundle.js`** (loaded on every desk page,
    built by `bench build`). Frappe only runs `work_item.js` when a form is opened, so a quick entry started from
    the list would otherwise use the default dialog.
31. **Status colours** are stored as hex; the list/form indicator name is computed on the server
    (`utils.nearest_indicator`, `api.get_status_indicators`).
32. **Default list filter** uses Frappe's `listview_settings.filters` (applied only when the user has no saved filters),
    for plain Tracker Users only.
33. **Work Item Summary** has two optional filters, *Closed From/To* (default last 30 days), to define "Closed in
    Period"; the spec lists none.
34. **Column order in the Time Entry list** follows the form field order (work item first); the spec's order
    (date first) can be set per user in List View Settings.
35. `tracker_default_tracker` and `tracker_project` live in their own *Auri PMS* section of Email Account.
36. **Default data** that Frappe would validate before `after_install` runs (Tracker Settings link defaults) is set in
    `after_install`, not as field defaults.

## Testing

37. **Tests run on the real site.** No MariaDB root access was available for a separate test site. Each class builds
    the fixture world once and every test runs inside a database savepoint that is rolled back, so nothing is left in
    the database (verified after each run). Anything that commits (for example the Email Queue sender) would break
    that isolation, which is why emails are queued per recipient. Tests also cope with existing data on the site.
38. **Frappe skips Version rows in tests** unless `ignore_version=False`; the test helper saves with it so the
    history checks (UAT-04, T-076) are real.
39. **92 spec tests + `test_e2e.py` + 18 additional tests** (UI API, global search, performance and indexes, lifecycle,
    the missing outgoing mail account, ERPNext permissions): 111 in total.
40. **UAT-01..08** are scripted in `test_e2e.py`. UAT-09..14 are covered by automated tests (T-050/T-064, T-119,
    T-084, T-096/T-097, T-120..T-125) and the Desk was exercised with a headless browser for the workspace, list,
    quick entry, form buttons, Log Time, Close/Reopen, Kanban, Gantt, Calendar, the four reports, the Project Tracker
    tab and the outsider's view; a consultant should still run the 14 scenarios by hand before go-live.

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
