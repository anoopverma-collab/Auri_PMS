// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

/* global auri_pms */
// Delivery & Health: projects, releases, sprints, tasks, workload and delivery health of every project the user manages.
// Its second tab, "Health and cost", is the former Portfolio (auri_portfolio.bundle.js): health score, budget, billing, risks and capacity.
let ui; // shared UI kit (auri_hub.bundle.js)

frappe.pages["management-dashboard"].on_page_load = function (wrapper) {
	frappe.require(["auri_hub.bundle.js", "auri_portfolio.bundle.js"], () => {
		ui = auri_pms.ui;
		wrapper.management = new ManagementDashboard(wrapper);
		wrapper.management.load();
	});
};

frappe.pages["management-dashboard"].on_page_show = function (wrapper) {
	if (wrapper.management) wrapper.management.load();
};

class ManagementDashboard {
	constructor(wrapper) {
		const { page, $body } = ui.initPage(wrapper, "Delivery & Health");
		this.page = page;
		this.$body = $body;
		this.options = { projects: [], releases: [], sprints: [] };
		this.applied = { project: [], release: "", sprint: "" };
		this.seq = 0;
		this.tab = "delivery";
		// Project takes several projects; Release and Sprint dropdowns list only what was created for the chosen ones
		const ids = (rows) => rows.map((r) => r.name);
		const scoped = () => {
			const chosen = this.f_project.get_value() || [];
			const all = ids(this.options.projects);
			return { project: ["in", chosen.length ? chosen : all.length ? all : [""]] };
		};
		const change = () => this.on_filter_change();
		this.f_project = page.add_field({
			fieldname: "project", label: __("Projects"), fieldtype: "MultiSelectList", change,
			get_data: () => this.options.projects.map((p) => ({ value: p.name, label: p.label, description: p.name })),
		});
		this.f_release = page.add_field({ fieldname: "release", label: __("Release"), fieldtype: "Link", options: "Release", change, get_query: () => ({ filters: scoped() }) });
		this.f_sprint = page.add_field({ fieldname: "sprint", label: __("Sprint"), fieldtype: "Link", options: "Sprint", change, get_query: () => ({ filters: scoped() }) });
	}

	values() {
		const chosen = this.f_project.get_value();
		return { project: Array.isArray(chosen) ? chosen : [], release: this.f_release.get_value() || "", sprint: this.f_sprint.get_value() || "" };
	}

	on_filter_change() {
		if (this.resetting) return;
		const cur = this.values();
		// other projects: a release or sprint that belongs to a project no longer chosen does not apply any more
		const stale = (name, rows) => cur.project.length && name && !cur.project.includes((rows.find((r) => r.name === name) || {}).project);
		if (JSON.stringify(cur.project) !== JSON.stringify(this.applied.project) && (stale(cur.release, this.options.releases) || stale(cur.sprint, this.options.sprints))) {
			this.resetting = true;
			Promise.all([
				stale(cur.release, this.options.releases) ? this.f_release.set_value("") : null,
				stale(cur.sprint, this.options.sprints) ? this.f_sprint.set_value("") : null,
			]).then(() => {
				this.resetting = false;
				this.load();
			});
			return;
		}
		// the Release and Sprint filters do not apply to the Health and cost tab, so only a new project reloads it
		const changed = this.tab === "health" ? JSON.stringify(cur.project) !== JSON.stringify(this.applied.project) : JSON.stringify(cur) !== JSON.stringify(this.applied);
		if (changed) this.load();
	}

	clear_filters() {
		this.resetting = true;
		Promise.all([this.f_project.set_value([]), this.f_release.set_value(""), this.f_sprint.set_value("")]).then(() => {
			this.resetting = false;
			this.load();
		});
	}

	load() {
		this.page.clear_inner_toolbar();
		this.page.clear_menu();
		ui.applyTheme(this.$body);
		this.inject_style();
		this.page.add_inner_button(__("Project Hub"), () => frappe.set_route("project-hub"));
		this.page.add_inner_button(__("Clear filters"), () => this.clear_filters());
		this.page.add_inner_button(__("Refresh"), () => this.load());
		ui.addThemeMenu(this.page, () => this.load());
		// the old Portfolio route sends people here with ?tab=health
		if (frappe.route_options && frappe.route_options.tab) {
			this.tab = frappe.route_options.tab === "health" && frappe.boot.auri_pms_health_cost ? "health" : "delivery";
			frappe.route_options = null;
		}
		if (this.tab === "health" && !frappe.boot.auri_pms_health_cost) this.tab = "delivery";
		if (this.tab === "health") ui.addPeriodMenu(this.page, () => this.load());
		if (!frappe.boot.auri_pms_portfolio) {
			this.$body.html(`<div class="hub-panel p-4"><h6>${__("Delivery & Health")}</h6><div class="text-muted">${__("Delivery & Health is for people who are members of an Auri PMS project, and for Auri PMS Admins.")}</div></div>`);
			return;
		}
		if (this.tab === "health") return this.load_health();
		this.$body.html(`<div class="text-muted p-4">${__("Loading...")}</div>`);
		const seq = ++this.seq;
		const filters = this.values();
		frappe.xcall("auri_pms.auri_pms.api.get_management_dashboard", { ...filters, project: JSON.stringify(filters.project) }).then((data) => {
			if (seq !== this.seq) return; // a newer request is on its way
			this.data = data;
			this.options = data.options;
			this.applied = { project: data.filters.projects, release: data.filters.release, sprint: data.filters.sprint };
			this.render();
		});
	}

	// The two views of the page: delivery (releases, sprints, tasks, people) and health and cost (the former Portfolio).
	tabs_html() {
		// Health and cost follows Project Role > Can See Health & Cost
		const tabs = [["delivery", __("Delivery")]];
		if (frappe.boot.auri_pms_health_cost) tabs.push(["health", __("Health and cost")]);
		return `<div class="md-tabs">${tabs.map(([key, label]) => `<span class="${this.tab === key ? "active" : ""}" data-tab="${key}">${label}</span>`).join("")}</div>`;
	}

	bind_tabs() {
		this.$body.find(".md-tabs span").on("click", (e) => {
			const tab = $(e.currentTarget).data("tab");
			if (tab === this.tab) return;
			this.tab = tab;
			this.load();
		});
	}

	// Health and cost follows the Project filter; the Release and Sprint filters belong to the delivery tab only.
	load_health() {
		++this.seq; // drop any delivery response still on its way
		const project = this.values().project;
		this.applied = this.values();
		this.$body.html(`${this.tabs_html()}<div class="md-health"></div>`);
		this.bind_tabs();
		this.portfolio = new auri_pms.Portfolio(this.page, this.$body.find(".md-health"), project);
		this.portfolio.load();
	}

	render() {
		const d = this.data;
		const k = d.kpis;
		const esc = ui.esc;
		const { tile, panel } = ui;
		const date = (value) => (value ? frappe.datetime.str_to_user(value) : "–");
		const project_link = (row) => `<a class="md-nowrap" href="/desk/project-hub/${encodeURIComponent(row.name || row.project)}">${esc(row.project_label || row.project_name)}</a>`;
		const badge = (text, tone) => `<span class="md-badge md-${tone}">${esc(text)}</span>`;
		const pbar = (value) => `<div class="md-pbar" title="${Math.round(value)}%"><i style="width:${Math.max(0, Math.min(100, value))}%"></i><b>${Math.round(value)}%</b></div>`;
		const num = (value, tone) => (value ? `<b class="${tone || ""}">${value}</b>` : `<span class="text-muted">0</span>`);
		const chosen = d.filters.projects; // the tiles open lists of the chosen projects only
		const wi = (extra) => ui.go("Work Item", { ...(chosen.length ? { project: ["in", chosen] } : {}), ...extra });
		const pj = (extra) => ui.go("Project", { pms_enabled: 1, ...(chosen.length ? { name: ["in", chosen] } : {}), ...extra });
		// a tile opens the list of exactly the records it counts (an empty list when the count is 0, like the other tiles)
		const ids = (doctype, names) => ui.go(doctype, { name: ["in", names.length ? names : ["-"]] });
		const overdue_filter = { is_closed: 0, due_date: ["<", d.today] };

		const label_of = (rows, name) => (rows.find((r) => r.name === name) || {}).label || name;
		const scope_note = [
			d.filters.projects.length ? `${d.filters.projects.length === 1 ? __("Project") : __("Projects")}: ${d.filters.projects.map((p) => esc(label_of(d.options.projects, p))).join(", ")}` : "",
			d.filters.release ? `${__("Release")}: ${esc(label_of(d.options.releases, d.filters.release))}` : "",
			d.filters.sprint ? `${__("Sprint")}: ${esc(label_of(d.options.sprints, d.filters.sprint))}` : "",
		].filter(Boolean).map((t) => ` · <b>${t}</b>`).join("");
		const header = `<div class="hub-title"><h4>${__("Delivery & Health")}</h4><span class="text-muted">${k.projects === 1 ? __("1 project") : __("{0} projects", [k.projects])} · ${__("Auri PMS enabled")} · ${frappe.datetime.str_to_user(d.today)}${scope_note}</span></div>`;

		// ---- project overview
		const projects_tiles = `<div class="hub-tiles">
			${tile(k.projects, __("Total projects"), "hub-blue", "", pj({}))}
			${tile(k.active, __("Active projects"), "hub-teal", k.cancelled ? __("{0} cancelled", [k.cancelled]) : "", pj({ status: "Open" }))}
			${tile(k.completed, __("Completed projects"), "hub-green", "", pj({ status: "Completed" }))}
			${tile(k.delayed, __("Delayed projects"), k.delayed ? "hub-red" : "hub-teal", __("overdue release, sprint or task"), ids("Project", d.ids.delayed_projects))}
		</div>`;

		// ---- task overview
		const tasks_tiles = `<div class="hub-tiles md-tiles5">
			${tile(k.tasks_total, __("Total tasks"), "hub-blue", "", wi({}))}
			${tile(k.tasks_open, __("Open tasks"), "hub-purple", "", wi({ is_closed: 0 }))}
			${tile(k.tasks_in_progress, __("In progress"), "hub-orange", "", wi({ status: "In Progress" }))}
			${tile(k.tasks_completed, __("Completed"), "hub-green", "", wi({ is_closed: 1 }))}
			${tile(k.tasks_overdue, __("Overdue"), k.tasks_overdue ? "hub-red" : "hub-teal", "", wi(overdue_filter))}
		</div>`;

		// ---- project-wise progress
		const projects_table = ui.table(
			d.projects,
			[__("Project"), __("Status"), __("Progress"), __("Open"), __("Overdue"), __("Releases"), __("Open sprints"), __("Next release due")],
			(p) => `<tr class="${p.delayed ? "md-row-late" : ""}">
				<td>${project_link(p)} <small class="text-muted">${esc(p.identifier || "")}</small></td>
				<td>${p.delayed ? badge(__("Delayed"), "red") : badge(__(p.status), p.status === "Completed" ? "green" : p.status === "Cancelled" ? "grey" : "blue")}${p.delayed ? `<small class="text-muted d-block">${p.delay_reasons.map(esc).join(", ")}</small>` : ""}</td>
				<td>${pbar(p.progress)}</td>
				<td>${num(p.open)}</td>
				<td>${num(p.overdue, "md-bad")}</td>
				<td>${p.releases_closed}/${p.releases}${p.releases_overdue ? ` ${badge(__("{0} overdue", [p.releases_overdue]), "red")}` : ""}</td>
				<td>${num(p.sprints_open)}</td>
				<td>${date(p.next_due)}</td></tr>`
		);

		// ---- release-wise tracking, with the tasks of each release
		const release_rows = d.releases.map((r) => {
			const late = r.late_days ? (r.status === "Closed" ? __("{0} d late", [r.late_days]) : __("{0} d overdue", [r.late_days])) : "";
			return `<tr class="${r.late ? "md-row-late" : ""}">
				<td>${project_link(r)}</td>
				<td>${ui.link("Release", r.name, r.release_name)}</td>
				<td>${badge(__(r.status), r.status === "Closed" ? "green" : r.late ? "red" : r.status === "Locked" ? "amber" : "blue")}</td>
				<td>${date(r.planned)}</td>
				<td>${r.actual ? date(r.actual) : "–"}${late ? `<small class="${r.status === "Closed" ? "text-muted" : "md-bad"} d-block">${late}</small>` : ""}</td>
				<td>${pbar(r.percent)}</td>
				<td>${r.completed}/${r.total}</td>
				<td>${num(r.open)}</td>
				<td>${num(r.overdue, "md-bad")}</td>
				<td>${r.sprints_open}/${r.sprints_total}${r.sprints_overdue ? ` ${badge(__("{0} overdue", [r.sprints_overdue]), "red")}` : ""}</td></tr>`;
		});
		const nr = d.no_release;
		if (nr.total) {
			release_rows.push(`<tr><td colspan="5" class="text-muted">${__("Tasks without a release")}</td><td></td><td>${nr.completed}/${nr.total}</td><td>${num(nr.open)}</td><td>${num(nr.overdue, "md-bad")}</td><td></td></tr>`);
		}
		const releases_table = d.releases.length || nr.total
			? `<table class="table table-sm hub-table"><thead><tr>${[__("Project"), __("Release"), __("Status"), __("Planned"), __("Actual"), __("Completion"), __("Done / tasks"), __("Open"), __("Overdue"), __("Sprints open / total")].map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${release_rows.join("")}</tbody></table>`
			: `<div class="text-muted small">${__("No releases yet")}</div>`;

		// ---- sprints, with the tasks of each sprint
		const sprints_table = ui.table(
			d.sprints,
			[__("Project"), __("Sprint"), __("Releases"), __("Status"), __("Planned"), __("Progress"), __("Done / tasks"), __("Open"), __("Overdue")],
			(s) => `<tr class="${s.late ? "md-row-late" : ""}">
				<td>${project_link(s)}</td>
				<td>${ui.link("Sprint", s.name, s.sprint_name)}</td>
				<td>${s.releases.length ? s.releases.map(esc).join(", ") : "–"}</td>
				<td>${badge(__(s.status), s.status === "Completed" ? "green" : s.late ? "red" : s.status === "Active" ? "teal" : "blue")}${s.late ? ` ${badge(__("Overdue"), "red")}` : ""}</td>
				<td>${date(s.start)} → ${date(s.end)}</td>
				<td>${pbar(s.percent)}</td>
				<td>${s.completed}/${s.total}</td>
				<td>${num(s.open)}</td>
				<td>${num(s.overdue, "md-bad")}</td></tr>`
		);

		// ---- people
		const max_pending = Math.max(1, ...d.users.map((u) => u.pending));
		const users_table = ui.table(
			d.users,
			[__("Person"), __("Assigned"), __("Pending"), __("In progress"), __("Overdue"), __("Open hours"), __("Projects"), __("Workload")],
			(u) => `<tr>
				<td>${u.user ? esc(u.full_name) : `<span class="text-muted">${esc(u.full_name)}</span>`}</td>
				<td>${u.assigned}</td>
				<td>${num(u.pending)}</td>
				<td>${num(u.in_progress)}</td>
				<td>${num(u.overdue, "md-bad")}</td>
				<td>${u.open_hours}</td>
				<td>${u.projects}</td>
				<td class="md-wl"><div class="md-pbar md-wlbar"><i class="${u.overdue ? "md-late" : ""}" style="width:${(u.pending / max_pending) * 100}%"></i></div></td></tr>`
		);

		// ---- hours: estimated against actual and billable, per project
		const hrs = d.hours;
		const h1 = (v) => (v === null || v === undefined ? "–" : `${flt(v, 1)}`);
		const over = (r) => (r.estimated && r.variance > 0 ? "md-bad" : "");
		const hour_row = (r, bold) => `<tr${bold ? ' class="md-total"' : ""}><td>${bold ? `<b>${__("Total")}</b>` : project_link({ name: r.name, project_label: r.label })}</td>
			<td>${h1(r.estimated)}</td><td>${h1(r.actual)}</td><td>${h1(r.billable)}</td>
			<td>${r.billable_pct === null ? "–" : `${flt(r.billable_pct, 0)}%`}</td>
			<td class="${over(r)}">${r.estimated || r.actual ? `${r.variance > 0 ? "+" : ""}${h1(r.variance)}` : "–"}</td></tr>`;
		const hours_table = `<table class="table table-sm hub-table"><thead><tr>${[__("Project"), __("Estimated (h)"), __("Actual (h)"), __("Billable (h)"), __("Billable of actual"), __("Actual vs estimate (h)")].map((h) => `<th>${h}</th>`).join("")}</tr></thead>
			<tbody>${hrs.projects.map((r) => hour_row(r)).join("")}${hrs.projects.length > 1 ? hour_row(hrs.total, true) : ""}</tbody></table>`;
		const hours_panel = hrs.total.estimated || hrs.total.actual
			? panel(__("Hours by project"), `<div class="hub-chart" id="md-hours"></div>${hours_table}`)
			: panel(__("Hours by project"), `<div class="text-muted small">${__("No estimates or time logged yet")}</div>`);

		// ---- delivery health
		const up = d.upcoming;
		// one row = [tag] [name over its detail] [when or why], so each column lines up down the list
		const li = (tag, main, meta, when) => `<li>${tag ? `<span class="md-tag">${tag}</span>` : ""}<div class="md-main">${main}<small class="text-muted">${meta}</small></div><div class="md-when">${when}</div></li>`;
		const upcoming_html = [
			...up.releases.map((r) => li(badge(__("Release"), "blue"), ui.link("Release", r.name, r.release_name), esc(r.project_label), date(r.planned))),
			...up.sprints.map((s) => li(badge(__("Sprint"), "teal"), ui.link("Sprint", s.name, s.sprint_name), esc(s.project_label), date(s.end))),
			...up.tasks.map((t) => li(badge(__("Task"), "grey"), ui.link("Work Item", t.name, `${t.name} ${t.subject}`), esc(t.assigned_to || __("Unassigned")), date(t.due_date))),
		];
		const delayed_html = d.delayed_releases.map((r) => li("", ui.link("Release", r.name, r.release_name), esc(r.project_label), `<span class="md-bad">${__("{0} d overdue", [r.late_days])}</span>`));
		const pending_html = d.pending.map((t) => li("", ui.link("Work Item", t.name, `${t.name} ${t.subject}`), esc(t.project_label), `${t.assigned_to ? "" : badge(__("Unassigned"), "amber")}${t.waiting_on_client ? badge(__("Waiting on client"), "amber") : ""}`));
		const list = (rows, empty) => (rows.length ? `<ul class="md-list">${rows.join("")}</ul>` : `<div class="text-muted small">${empty}</div>`);
		const health_tiles = `<div class="hub-tiles md-tiles5">
			${tile(k.releases_overdue, __("Delayed releases"), k.releases_overdue ? "hub-red" : "hub-teal", __("of {0} releases", [k.releases]), ids("Release", d.ids.delayed_releases))}
			${tile(k.sprints_overdue, __("Overdue sprints"), k.sprints_overdue ? "hub-red" : "hub-teal", __("of {0} sprints", [k.sprints]), ids("Sprint", d.ids.overdue_sprints))}
			${tile(k.pending_activities, __("Pending activities"), k.pending_activities ? "hub-orange" : "hub-teal", __("unassigned or waiting on client"), ids("Work Item", d.ids.pending))}
			${tile(k.unassigned, __("Unassigned tasks"), k.unassigned ? "hub-orange" : "hub-teal", "", wi({ is_closed: 0, assigned_to: ["is", "not set"] }))}
			${tile(k.waiting_on_client, __("Waiting on client"), k.waiting_on_client ? "hub-orange" : "hub-teal", "", ui.goReport("Client Dependencies"))}
		</div>`;

		const section = (title, note, body) => `<div class="md-sec"><h5>${title}</h5>${note ? `<span>${note}</span>` : ""}</div>${body}`;
		this.$body.html(`${this.tabs_html()}${header}
			${section(__("Project overview"), "", projects_tiles)}
			${section(__("Task overview"), __("all projects"), tasks_tiles)}
			${section(__("Project-wise progress"), __("delayed projects first"), panel(__("Projects"), projects_table))}
			${section(__("Hours: estimated vs actual vs billable"), __("all time · estimated on the tickets · actual = time logged · billable = the billable part of it"), hours_panel)}
			${section(__("Release-wise tracking"), __("planned = due date · actual = day the last ticket closed"), panel(__("Releases"), releases_table))}
			${section(__("Sprint overview"), __("a sprint belongs to the releases of its tickets"), panel(__("Sprints"), sprints_table))}
			${section(__("User-wise workload"), __("Assigned To and Additional Assignees"), panel(__("People"), users_table))}
			${section(__("Delivery health"), __("next {0} days", [d.upcoming_days]), health_tiles)}
			<div class="md-grid">
				${panel(__("Upcoming deadlines"), list(upcoming_html, __("Nothing due in the next {0} days", [d.upcoming_days])))}
				${panel(__("Delayed releases"), list(delayed_html, __("No release is overdue")))}
				${panel(__("Pending activities"), list(pending_html, __("Everything open is assigned and moving")))}
			</div>`);
		ui.bindTiles(this.$body);
		this.bind_tabs();
		if (hrs.total.estimated || hrs.total.actual) {
			ui.chart(this.$body, "#md-hours", {
				type: "bar",
				data: {
					labels: hrs.projects.map((r) => r.label),
					datasets: [
						{ name: __("Estimated"), values: hrs.projects.map((r) => r.estimated) },
						{ name: __("Actual"), values: hrs.projects.map((r) => r.actual) },
						{ name: __("Billable"), values: hrs.projects.map((r) => r.billable) },
					],
				},
				colors: [ui.PALETTE.purple, ui.PALETTE.orange, ui.PALETTE.green],
				barOptions: { spaceRatio: 0.35 },
				axisOptions: { xIsSeries: 1 },
			});
		}
	}

	inject_style() {
		if ($("#md-style-v5").length) return;
		$(`<style id="md-style-v5">
			.auri-hub .md-tabs { display: flex; gap: 6px; margin: 4px 0 14px; }
			.auri-hub .md-tabs span { padding: 5px 14px; border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer; color: var(--g-muted, #8a94a6); background: rgba(120, 130, 150, .14); }
			.auri-hub .md-tabs span.active { color: #fff; background: var(--g-acc, #6366f1); }
			.auri-hub .md-sec { display: flex; align-items: baseline; gap: 12px; margin: 26px 0 10px; }
			.auri-hub .md-sec h5 { margin: 0; font-weight: 700; }
			.auri-hub .md-sec span { color: var(--g-muted, #8a94a6); font-size: 12px; }
			.auri-hub .md-badge { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; white-space: nowrap; }
			.auri-hub .md-red { background: #fde8e8; color: #b42318; }
			.auri-hub .md-amber { background: #fff4d6; color: #93640a; }
			.auri-hub .md-green { background: #dcf5e4; color: #166534; }
			.auri-hub .md-blue { background: #e0ecff; color: #1d4ed8; }
			.auri-hub .md-teal { background: #d7f3f0; color: #0f766e; }
			.auri-hub .md-grey { background: #eceff3; color: #475467; }
			.auri-hub .md-bad { color: #b42318; }
			.auri-hub .md-total > td { border-top: 2px solid rgba(120, 130, 150, .35); }
			.auri-hub .md-row-late > td:first-child { box-shadow: inset 3px 0 0 #d92d20; }
			.auri-hub .md-pbar { position: relative; height: 16px; min-width: 90px; border-radius: 8px; background: rgba(120, 130, 150, .18); overflow: hidden; }
			.auri-hub .md-pbar i { position: absolute; inset: 0 auto 0 0; background: #2e90fa; border-radius: 8px; }
			.auri-hub .md-pbar i.md-late { background: #f79009; }
			.auri-hub .md-pbar b { position: relative; display: block; text-align: center; font-size: 10px; line-height: 16px; }
			.auri-hub .md-wlbar { height: 10px; min-width: 120px; }
			.auri-hub .md-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; margin-top: 4px; }
			.auri-hub .md-list { list-style: none; margin: 0; padding: 0; }
			.auri-hub .md-list li { display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; border-bottom: 1px solid rgba(120, 130, 150, .18); font-size: 12px; }
			.auri-hub .md-tag { flex: 0 0 68px; padding-top: 1px; }
			.auri-hub .md-main { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 1px; line-height: 1.35; }
			.auri-hub .md-when { flex: 0 0 auto; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; white-space: nowrap; text-align: right; }
			.auri-hub .md-nowrap, .auri-hub .hub-table th { white-space: nowrap; }
			.auri-hub .hub-tiles.md-tiles5 { grid-template-columns: repeat(5, minmax(0, 1fr)); }
			@media (max-width: 1100px) { .auri-hub .hub-tiles.md-tiles5 { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); } }
			.auri-hub .hub-table td, .auri-hub .hub-table th { vertical-align: middle; }
		</style>`).appendTo("head");
	}
}
