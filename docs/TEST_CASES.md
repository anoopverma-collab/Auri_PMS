# Auri PMS: functional test cases

Covers Delivery & Health (with its Health and cost tab, the former Portfolio), the Quality Dashboard, the sidebar and
the *Can See All Work Items* tick on the Project Role. **Auto** cases are run by `bench --site <site> run-tests --app auri_pms`; **Manual**
cases need a browser (the UI was not driven by a script).

Fixture users used below: **Admin** (Auri PMS Admin), **Manager** (Manager on Alpha and Beta), **Dev** (Developer on Alpha),
**Outsider** (no allocation). Alpha is private, Beta is public, Gamma has Auri PMS switched off.

Test modules: `tests/test_management.py` (MD), `tests/test_functional_scope.py` (FS), `tests/test_permissions.py` (PM).

## 1. Access

| ID | Case | Steps | Expected | Type / test |
|---|---|---|---|---|
| ACC-01 | Admins and project managers open Delivery & Health | Open it as Admin, then as Manager | Opens. Admin lists all PMS projects, Manager lists Alpha and Beta | Auto: MD `test_only_admins_and_project_managers_get_it` |
| ACC-02 | A developer or outsider is refused | Open it as Dev, then as Outsider | "not permitted" message; no data returned | Auto: MD same; FS `test_the_same_users_are_refused_by_both` |
| ACC-03 | A project without Auri PMS never appears | Open as Admin | Gamma is not listed | Auto: MD same test |
| ACC-04 | The sidebar link is hidden for non-managers | Log in as Dev | No Delivery & Health entry in the sidebar | E2E ACC-04 (needs a denied user, see section 9) |
| ACC-05 | Health and cost follows the same rule | Call Health and cost as Admin, Manager, Dev, Outsider | Admin and Manager get data; Dev and Outsider are refused | Auto: FS `test_the_same_users_are_refused_by_both`, `test_the_health_tab_boot_flag_matches_the_dashboard_access` |
| ACC-06 | Real users | Call every dashboard as each real user of the site | Managers and admins get data; others get "denied"; no errors | Done once on `standard-v16.local` (15 users): no errors |

## 2. Delivery & Health: Delivery tab

| ID | Case | Steps | Expected | Type / test |
|---|---|---|---|---|
| MD-01 | Task counts | Create an open overdue ticket and an In Progress ticket | Total, open, in progress and overdue rise by the right amounts | Auto: MD `test_task_counts` |
| MD-02 | Overdue release delays its project | Give a release a past due date, leave it Open | Project shows Delayed with the reason; delayed count and delayed releases list include it | Auto: MD `test_an_overdue_release_delays_its_project` |
| MD-03 | Actual release date | Close the last ticket of a release on a past day | Actual date equals that day; it is not marked late when it closed on time | Auto: MD `test_a_closed_release_reports_when_it_really_finished` |
| MD-04 | Overdue sprint | Give a sprint a past end date | Sprint is Overdue; it lists the releases of its tickets | Auto: MD `test_an_overdue_sprint_and_the_releases_of_its_tickets` |
| MD-05 | Workload per person | Assign tickets, add an additional assignee | Both are counted; unassigned tickets show as their own row | Auto: MD `test_workload_per_person_counts_assigned_and_additional` |
| MD-06 | Pending activities | Leave a ticket unassigned; mark another waiting on the client | Both appear under Pending activities | Auto: MD `test_pending_activities_are_unassigned_or_waiting_on_the_client` |
| MD-07 | Upcoming deadlines | Create items due in 3 days and in 30 days | Only the first is listed (14-day window) | Auto: MD `test_upcoming_deadlines_cover_the_next_two_weeks` |
| MD-13 | Hours: estimated vs actual vs billable | Per project: estimated (tickets), actual (time logged), billable, billable %, actual vs estimate, plus a total | Auto: MD `test_hours_estimated_against_actual_and_billable`; E2E MD-13, MD-14 |
| MD-14 | No time yet | A project with no time shows no billable share | Auto: MD `test_a_project_with_no_time_has_no_billable_share` |
| MD-15 | Hours follow the filters | A release or sprint keeps the time logged on its tickets; a project shows its own row only | Auto: MD `test_the_hours_follow_the_filters` |
| MD-08 | Tiles open the matching list | Click Open tasks, Overdue, Waiting on client | The Work Item list opens with the same filter and the same count | Manual |
| MD-09 | Tab switch | Click Health and cost, then Delivery | The right view shows each time; no stale content | E2E MD-09 |

## 3. Delivery & Health: filters

| ID | Case | Steps | Expected | Type / test |
|---|---|---|---|---|
| FLT-16 | Several projects | A list, comma-separated names or a JSON list narrow the page to exactly those projects; a repeated name counts once | Auto: MD `test_several_projects_can_be_chosen` |
| FLT-17 | Totals | Tasks, releases and hours cover only the chosen projects | Auto: MD `test_the_totals_cover_only_the_chosen_projects` |
| FLT-18 | Releases and sprints | Offered only for the chosen projects; the project list never shrinks | Auto: MD `test_releases_and_sprints_are_offered_only_for_the_chosen_projects` |
| FLT-19 | Release across projects | A release of one of the chosen projects is fine; one of an un-chosen project is refused | Auto: MD `test_a_release_must_belong_to_one_of_the_chosen_projects` |
| FLT-20 | Bad project in the list | The whole request is refused | Auto: MD `test_a_bad_project_in_the_list_refuses_the_whole_request` |
| FLT-21 | Multi-select in the browser | The Projects box lists every managed project, one or two can be ticked, the header and tiles follow, Clear filters empties it | E2E FLT-01, FLT-03 to FLT-06, FLT-13 |
| FLT-01 | No filter | Open with all three empty | Every project, release and sprint is offered | Auto: MD `test_without_filters_every_project_release_and_sprint_is_offered` |
| FLT-02 | Project-wise dropdowns | Choose Alpha | The Release and Sprint dropdowns list only Alpha's records | Auto: MD `test_the_dropdowns_list_only_what_was_created_for_the_chosen_project`, `test_the_link_field_dropdowns_are_project_wise_too` |
| FLT-03 | Project filter | Choose Alpha | Every block (tiles, tables, people, health) covers Alpha only | Auto: MD `test_a_project_filter_narrows_every_block` |
| FLT-04 | Release filter | Choose a release | Its tickets and the sprints holding them remain | Auto: MD `test_a_release_filter_keeps_that_release_its_tickets_and_its_sprints` |
| FLT-05 | Release with no sprint | Choose such a release | Sprint block is empty, no error | Auto: MD `test_a_release_without_a_sprint_leaves_the_sprint_block_empty` |
| FLT-06 | Sprint filter | Choose a sprint | Its tickets and their releases remain | Auto: MD `test_a_sprint_filter_keeps_that_sprint_and_the_releases_of_its_tickets` |
| FLT-07 | Release and Sprint together | Choose both | Intersection of the two | Auto: MD `test_release_and_sprint_together_are_an_intersection` |
| FLT-08 | Filters echoed | Apply any | The response names the applied filters; the header shows them | Auto: MD `test_the_filters_are_echoed_so_the_page_can_show_them` |
| FLT-09 | Wrong project | Send a release of Beta with project Alpha | Rejected | Auto: MD `test_a_release_or_sprint_of_another_project_is_refused` |
| FLT-10 | Outside the audience | Manager asks for Gamma | Permission error | Auto: MD `test_a_project_outside_the_audience_is_refused` |
| FLT-11 | Manager's options | Open as Manager | Only releases and sprints of managed projects are offered | Auto: MD `test_a_manager_is_offered_only_the_releases_of_the_projects_they_manage` |
| FLT-12 | Changing the project clears Release and Sprint | Pick release, then change the project | Release and Sprint reset; one reload, no flicker | Manual (logic checked with a Node script); E2E checks the Health tab reload (HC-10) |
| FLT-13 | Clear filters | Click Clear filters | All three empty; full data | E2E FLT-13 |
| FLT-14 | Burndown report | Sprint Burndown with Project Alpha and a Beta sprint | Error; dropdown lists Alpha's sprints only | Auto: MD `test_the_sprint_burndown_report_checks_the_project` |
| FLT-15 | Work Item cannot cross projects | Give a ticket a release of another project | Refused | Auto: MD `test_a_work_item_cannot_take_a_release_or_sprint_of_another_project` |

## 4. Health and cost tab (former Portfolio)

| ID | Case | Steps | Expected | Type / test |
|---|---|---|---|---|
| HC-01 | Same projects as Delivery | Compare both tabs as Admin and Manager | Same set of projects | Auto: FS `test_both_views_list_the_same_projects` |
| HC-02 | Same numbers | Compare projects, open, overdue and closed | Equal on both tabs | Auto: FS `test_both_views_agree_on_the_ticket_numbers` |
| HC-03 | Row numbers, status, totals, periods, trends | See the Portfolio tests | Unchanged by the move | Auto: `tests/test_portfolio.py` (18 tests) |
| HC-04 | Project filter focuses the tab | Choose Alpha on the page, open Health and cost | "Showing only" Alpha; Show all clears it | E2E HC-04 |
| HC-05 | Period menu | Change 1 / 3 / 6 months / Overall | Tab reloads for that range; Delivery tab has no period menu | Manual (the Range menu is visible on the health tab in the screenshot) |
| HC-06 | Panels | Health cards, trends, billing graph, capacity, ticket table, notes | All draw; clicks open the filtered lists; adding a note updates the card | E2E HC-06 (cards and table draw); clicks and notes Manual |
| HC-07 | Old route | Open `/desk/portfolio` or an old bookmark | Lands on Delivery & Health, Health and cost tab | Auto (script check): FS `test_the_old_portfolio_route_redirects_to_the_health_tab`; E2E HC-07 |
| HC-08 | Project Hub button | Click "Delivery & Health" in the Project Hub | Opens the dashboard | Auto: FS `test_the_project_hub_buttons_open_the_dashboard`; E2E HC-08 |
| HC-10b | Order of the blocks | Open Health and cost | Projects at a glance, then *Why this status* (a collapsed bar), then Trends by project, then Details | Manual (checked in a browser) |
| HC-11 | Health shown per screen | In a Project, tick or untick *Show on Project Hub*, *Show on Portfolio*, *Show on Report* | Each box switches the health level and score on its own screen only (Hub, the Health and cost tab, the client report); an unticked project shows a dash on the tab and is left out of its health counts | Auto: `tests/test_health_visibility.py` |
| HC-09 | Bundle is built | `bench build --app auri_pms` | `auri_portfolio.bundle.*.js` exists in `public/dist/js` | Auto (source): FS `test_the_dashboard_loads_the_health_bundle_that_exists`; E2E (the tab loads in a real browser) |

## 5. Quality Dashboard

| ID | Case | Steps | Expected | Type / test |
|---|---|---|---|---|
| QD-01 | All projects adds up | With no project chosen, compare with each project | Open, closed, opened-in-period and critical equal the sum of the projects | Auto: FS `test_the_all_projects_view_adds_up_every_visible_project` |
| QD-02 | Bug share | Add a bug and a task | Opened-in-period rises by 1; share is above 0 | Auto: FS `test_the_share_of_bugs_among_new_tickets_counts_all_projects` |
| QD-03 | Density | Log 4 hours | Bugs per 100 hours = bugs × 100 / 4 | Auto: FS `test_hours_logged_feed_the_bug_density` |
| QD-04 | Member sees own and public | Dev opens it with no project | Alpha and public projects; no private project they do not belong to | Auto: FS `test_a_member_sees_their_projects_and_the_public_ones_only` |
| QD-05 | Hidden project leaves totals unchanged | Add a bug to a private project | Dev's totals do not change | Auto: FS `test_the_private_project_does_not_change_a_members_totals` |
| QD-06 | Role box unticked | Untick Can See All Work Items on the Developer role | Dev counts only own or assigned bugs; Manager still sees all | Auto: FS `test_members_see_only_their_own_bugs_when_the_role_box_is_unticked` |
| QD-07 | Empty project | Choose a project with no tickets | "No bugs yet" message, zero tiles, no error | Auto: FS `test_a_project_without_tickets_gives_an_empty_dashboard` |
| QD-08 | No defect tracker | Untick Counts as Defect on every ticket type | "No defect tracker" message | Auto: FS `test_without_a_defect_tracker_the_dashboard_says_so` |
| QD-09 | Periods | 1m, 3m, 6m, Overall | Series length equals the labels | Auto: FS `test_every_period_works_for_all_projects` |
| QD-10 | Project dropdown | Open the dropdown as Admin, Dev, Outsider | Only PMS-enabled projects; Dev sees Alpha, Outsider sees Beta only; Gamma never | Auto: FS `test_the_project_dropdown_lists_only_projects_with_auri_pms`; E2E QD-10 (the real dropdown) |
| QD-11 | Same results as before the speed-up | Compare old and new code on the site data | Identical output (9 combinations checked) | Done once; existing tests in `tests/test_quality.py` (13) |
| QD-12 | Speed | Open with all projects on a large site | Opens quickly; no full ticket load | Manual |

## 6. Can See All Work Items (Project Role)

The site-wide *Members See All Work Items* setting was replaced by the *Can See All Work Items* tick on each Project Role; the cases below are the same, per role.

| ID | Case | Expected | Type / test |
|---|---|---|---|
| SET-01 | Ticked: a member sees every item of their projects | Auto: PM `test_ticked_a_member_sees_every_item_of_their_project` |
| SET-02 | The box is per role, so a Reporter sees only their own while a Developer sees all, and one person can differ per project | Auto: PM `test_the_box_is_per_role_so_a_reporter_sees_only_their_own`, `test_the_same_person_can_see_all_on_one_project_and_only_their_own_on_another` |
| SET-03 | Unticked: only items assigned to, raised by, or with the member as additional assignee | Auto: PM `test_unticked_a_member_sees_only_the_items_assigned_to_or_raised_by_them` |
| SET-04 | Unticked: opening someone else's item is refused | Auto: PM `test_unticked_a_member_cannot_open_an_item_assigned_to_someone_else` |
| SET-05 | Unticked: managers and admins unchanged | Auto: PM `test_unticked_a_manager_and_an_admin_still_see_everything` |
| SET-06 | Unticked: public project stays readable for a non-member | Auto: PM `test_unticked_a_public_project_stays_readable_for_a_non_member` |
| SET-07 | Unticked: a member can still create an item | Auto: PM `test_unticked_a_member_can_still_create_an_item` |
| SET-08 | Insights (raw SQL) follows the setting | Auto: FS `test_insights_follow_the_role_box_too`; Manual in the UI |

## 6b. Auri Insights scope

| ID | Case | Expected | Type / test |
|---|---|---|---|
| INS-01 | Dropdown | Lists the Auri PMS projects the user is allocated to (all for an admin) | Auto: FS `TestInsightsScope`; E2E INS-01 |
| INS-02 | Member | Sees their projects only; a public project they are not on, and a project without Auri PMS, are left out | Auto: FS `test_a_member_gets_their_projects_only` |
| INS-03 | Manager and admin | A manager gets the projects they are on; an admin gets every PMS project | Auto: FS `test_a_manager_gets_the_projects_they_are_on`, `test_an_admin_gets_every_pms_project` |
| INS-04 | No allocation | Empty dashboard, no error | Auto: FS `test_someone_with_no_allocation_gets_none`, `test_someone_with_no_allocation_sees_an_empty_dashboard_not_an_error` |
| INS-05 | Every report | All six reports cover only those projects | Auto: FS `test_every_report_covers_only_those_projects` |
| INS-06 | Outside the scope | Asking for another project is refused | Auto: FS `test_a_project_outside_the_scope_is_refused` |

## 6c. Auri PMS projects only, everywhere

| ID | Case | Expected | Type / test |
|---|---|---|---|
| SCP-01 | Every Project field of the app | Doctype fields carry a link filter on *Enable Auri PMS*; page, report and calendar fields carry a query | Auto: FS `test_every_project_link_of_the_app_is_limited_to_auri_pms_projects` |
| SCP-02 | A project switched off after it got records | Leaves the Quality Dashboard, and asking for it by name is refused | Auto: FS `test_quality_leaves_out_a_project_that_was_switched_off` |
| SCP-03 | Admin | Auri Insights, Delivery & Health, Health and cost and the Project Hub list the same Auri PMS projects | Auto: FS `test_every_dashboard_lists_the_same_pms_projects_for_an_admin` |
| SCP-04 | Dropdowns in the browser | Insights, Quality and Client Status Report list only Auri PMS projects | E2E INS-01, QD-10, SR-01 |

## 6d. Per-project configuration and access

| ID | Check | Expect |
|----|-------|--------|
| PA-01 | Enabled Statuses limits the Status dropdown and the save | only the project's statuses are offered; another is refused |
| PA-02 | Work Item with no project | Status and other project dropdowns show "Select a Project first" once and offer nothing |
| PA-03 | Module not enabled on the project | refused; the dropdown lists only the project's modules |
| PA-04 | Field rule: a role with Subject view only edits an existing item | refused on save (all five fields tested), allowed when ticked |
| PA-05 | Can See All Work Items unticked vs ticked per role, per project | own items only vs every item; Developer on Alpha and Reporter on Beta differ |
| PA-06 | New button table for Manager, Developer, an outsider and an admin | matches `CREATE_RULES`; system records are admin only |
| PA-07 | Project Module and Work Item Category lists | hidden from members who cannot manage them; dropdowns still work |
| PA-08 | Project Dashboard Snapshot of another project | not listed, not readable |
| PA-09 | Delivery & Health for a Developer and an outsider | a member sees their own project; an outsider is refused |
| PA-10 | Company User Permission on a member | dashboards and project dropdowns still list their project; unticked, they do not |
| PA-11 | Project Role list | the Permissions column lists capabilities and the view-only fields |
| PA-12 | Shipped roles: Can See Health & Cost and Can See Auri Insights | only Manager is ticked |
| PA-13 | Role without the ticks opens Health and cost data or an Insights report | refused; ticked, it works. Manager and admin work |
| PA-14 | Developer on Alpha (no ticks) and Manager on Beta | both areas cover Beta only |
| PA-15 | Someone on no project opens Insights | an empty list, not an error |
| PA-16 | Browser: Health and cost tab and the Insights sidebar entry | hidden for a role without the tick; the Insights page shows a message. Manual |
| PA-17 | Project Hub, Health view, role without Can See Health & Cost | the payload has no billable hours, hours by person or activity, billing categories, team people or per-person open tickets; hours spent and the other panes' data stay |
| PA-18 | Same call for Manager and admin | full figures, no `can_see_cost` flag |
| PA-19 | Hub by-period table without the tick | refused; with the tick it works |
| PA-20 | A saved History snapshot opened without the tick | the same figures are blanked; with the tick they show |
| PA-21 | Browser: Project Hub for a role without the tick | the Time and billing and People tabs are gone, and the hero, Overview tile and Work bars show no billable figures. Manual |
| PA-22 | Project Hub in the sidebar | listed after My Work, in both sidebar files and on the installed sidebar |
| PA-23 | My Work shortcut flag at login | true for an Auri PMS role or System Manager; false with the module blocked or without any of those roles |
| PA-24 | Browser: the My Work button | a green button in the page header right after the search button on ERPNext and PMS screens; it opens My Work, hides on My Work, stays after a form is saved or reopened, and looks right in light and dark mode and on a phone. Manual |

## 7. Sidebar and pages

| ID | Case | Expected | Type / test |
|---|---|---|---|
| NAV-01 | Order | Auri Insights, Delivery & Health, Client Status Report, My Work, then Masters, Reports, Settings (Project Hub and Quality Dashboard are not in the sidebar; their pages still open) | Auto: FS `test_insights_and_the_management_dashboard_come_first_and_the_portfolio_is_gone`; `tests/test_install.py` `test_t003_fixtures_exist` |
| NAV-02 | No Portfolio entry | Auto: same tests |
| NAV-03 | Both sidebar files agree | Auto: FS `test_both_sidebar_files_have_the_same_order` |
| NAV-04 | Installed sidebar equals the file | Auto: FS `test_the_installed_sidebar_matches_the_file` |
| NAV-05 | No dead links | Every item opens an existing page, DocType or report | Auto: FS `test_every_sidebar_link_opens_something` |
| NAV-06 | Pages are open to the PMS roles | Auto: FS `test_the_dashboard_pages_exist_for_the_pms_roles` |
| NAV-07 | A site-saved sidebar arrangement overrides the file | Manual: after changing the order in the app, check *Custom Sidebar* on the site; entries missing from it are added at the end |
| NAV-08 | Sidebar in the browser | E2E NAV-08 and NAV-02 |

## 7b. Client Status Report preview

| ID | Case | Steps | Expected | Type |
|---|---|---|---|---|
| CSR-01 | The preview uses the whole pane | Open Client Status Report with any layout (Summary, Detailed, Original) | The report fills the Preview pane's width; no grey margin on either side | Manual (not yet in the browser suite) |
| CSR-02 | The sent report keeps its width | Email or download the same report | The email and PDF keep the layout's own width (640 to 720 px); only the on-screen preview is widened | Manual |

## 8. Browser checks (Playwright)

`e2e/dashboards.py` drives a real Chromium against the running bench, read-only (it creates and changes no record; screenshots go to
`e2e/screenshots`, which git ignores). It logs in with a session id made by `e2e/sessions.py`, so no password is used. 22 checks pass:
sidebar order and no Portfolio entry (NAV-02, NAV-08), tiles equal the server's numbers (MD-01), every section draws (MD-10), a tile
opens its list (MD-08), the tab switch (MD-09), Project, Release and Sprint dropdowns narrow project-wise (FLT-01, FLT-02, FLT-03),
Clear filters (FLT-13), the Health and cost tab and its filter (HC-04, HC-06, HC-10), the old Portfolio route and the Project Hub
button (HC-07, HC-08), the Quality Dashboard's Project dropdown (QD-10), no script errors (MD-00, QD-13), dark mode and phone width
(UI-01, UI-02).

Run it from the bench folder with `SESSIONS` set to the output of `e2e/sessions.py` (the header of `e2e/dashboards.py` has the full command). Add `MANAGER=<user>` and `DENIED=<user>` to
also check the manager and the refused user (ACC-01, ACC-02, ACC-04).

The first run found a real defect (HC-10): opening Health and cost while a Release was chosen reloaded the tab twice and the charts
printed about 100 script errors. Fixed: only a new Project reloads that tab.

## 9. Test data

`e2e/test_data.py` creates labelled test data for the Auri PMS projects and can remove exactly what it made. Every record is named
"[TEST] ...", its name is written to `e2e/test_data_created.json` (git ignores it), and nothing existing is changed. Per project it makes
3 modules, 3 releases (finished, overdue, upcoming), 3 sprints (completed, active, planned), 15 tickets (bugs, tasks, features and
support across statuses, priorities, overdue, unassigned and waiting on the client), 10 time entries (billable and non-billable) and 3 risks.
E-mails are muted and tickets go only to the project's manager.

    cd sites
    ../env/bin/python ../apps/auri_pms/e2e/test_data.py <site> make PROJ-0035 PROJ-0036
    ../env/bin/python ../apps/auri_pms/e2e/test_data.py <site> remove

## 10. Known limits

* The browser checks run as the Administrator only. The manager and refused-user checks (ACC-01, ACC-02, ACC-04) need two test users; they are written but have not been run, because minting a login for a real user was refused. Create two dedicated test users or name two users you allow.
* Run the browser checks like this: `SESSIONS=$(cd sites && ../env/bin/python ../apps/auri_pms/e2e/sessions.py <site> Administrator) SITE=<site> URL=http://localhost:8002 python3 apps/auri_pms/e2e/dashboards.py`.
* The **Client Status Report preview** width (CSR-01, CSR-02) and the order of the Health and cost blocks (HC-10b) are checked by hand, not in the browser suite.
* The test data ("[TEST]" records) lowers the health score on purpose: overdue tickets, a past-due release, a sprint behind and open risks. A project with them can show 0 ("Off Track"). `e2e/test_data.py remove` deletes only those records.
* What stays **Manual**: tile counts compared with the list, notes and drill-down clicks on the health tab, theme menu, the speed on a large site.
* The test setup puts the shipped statuses and Project Role capabilities back inside each test (rolled back), so a site's own extra status (for example "Dev complete") or a tuned role no longer breaks the suite.
