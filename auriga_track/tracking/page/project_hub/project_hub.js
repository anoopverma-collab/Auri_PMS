// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// Project Hub: pick a project, then work inside it (tickets, board, sprints, releases, team, time, reports).
const HUB_API = "auriga_track.tracking.api";

/* global auriga_track */
let ui; // shared UI kit, available once auriga_hub.bundle.js has loaded

frappe.pages["project-hub"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Project Hub"), single_column: true });
	frappe.require("auriga_hub.bundle.js", () => {
		ui = auriga_track.ui;
		wrapper.project_hub = new ProjectHub(page, wrapper);
		const route = frappe.get_route();
		wrapper.project_hub.show(route[1], route[2]);
	});
};

frappe.pages["project-hub"].on_page_show = function (wrapper) {
	if (!wrapper.project_hub) return; // the first render happens when the bundle has loaded
	const route = frappe.get_route();
	wrapper.project_hub.show(route[1], route[2]);
};

class ProjectHub {
	constructor(page, wrapper) {
		this.page = page;
		this.$body = $(`<div class="auriga-hub"></div>`).appendTo(page.main);
		ui.injectStyle();
		ui.applyTheme(this.$body);
	}

	show(project, view) {
		this.view = view === "health" ? "health" : "overview";
		this.page.clear_primary_action();
		this.page.clear_inner_toolbar();
		this.page.clear_menu();
		this.route_project = project;
		ui.applyTheme(this.$body);
		this.$body.html(`<div class="text-muted p-4">${__("Loading...")}</div>`);
		if (project) this.load_project(decodeURIComponent(project));
		else this.load_projects();
	}

	// ------------------------------------------------------------------ project picker
	load_projects() {
		this.page.set_title(__("Project Hub"));
		this.page.set_indicator("");
		frappe.xcall(`${HUB_API}.get_hub_projects`).then((projects) => {
			this.projects = projects;
			this.$body.html(`
				<div class="hub-title"><h4>${__("Project Hub")}</h4><span class="text-muted">${__("Pick a project to see its tickets, sprints, releases and team.")}</span></div>
				<div class="hub-search"><input type="text" class="form-control" placeholder="${__("Search projects")}"></div>
				<div class="hub-grid"></div>`);
			this.$body.find("input").on("input", (e) => this.render_cards($(e.target).val()));
			this.render_cards("");
			this.page.add_inner_button(__("Portfolio"), () => frappe.set_route("portfolio"));
			this.page.add_inner_button(__("My Work"), () => frappe.set_route("my-work"));
			this.page.add_inner_button(__("Quality"), () => frappe.set_route("quality-dashboard"));
			ui.addThemeMenu(this.page, () => this.show(this.route_project, this.view));
		});
	}

	render_cards(filter) {
		const q = (filter || "").toLowerCase();
		const rows = this.projects.filter((p) => `${p.project_name} ${p.tracker_identifier || ""}`.toLowerCase().includes(q));
		const $grid = this.$body.find(".hub-grid").empty();
		if (!rows.length) {
			$grid.html(`<div class="text-muted">${__("No projects found. Ask a project manager to add you as a member.")}</div>`);
			return;
		}
		rows.forEach((p) => {
			const sprint = p.active_sprint
				? `<div class="hub-sprint"><span>${frappe.utils.escape_html(p.active_sprint.name)}</span>
					<div class="progress"><div class="progress-bar" style="width:${flt(p.active_sprint.percent_complete)}%"></div></div></div>`
				: `<div class="text-muted small">${__("No active sprint")}</div>`;
			const ident = p.tracker_identifier
				? `<span class="hub-ident">${frappe.utils.escape_html(p.tracker_identifier)}</span>`
				: `<span class="hub-ident hub-warn">${__("No identifier")}</span>`;
			const $card = $(`
				<div class="hub-card" tabindex="0">
					<div class="hub-card-head"><b>${frappe.utils.escape_html(p.project_name || p.name)}</b>${ident}</div>
					<div class="hub-stats">
						<div><b>${p.open}</b><span>${__("Open")}</span></div>
						<div class="${p.overdue ? "text-danger" : ""}"><b>${p.overdue}</b><span>${__("Overdue")}</span></div>
						<div><b>${p.mine}</b><span>${__("Mine")}</span></div>
						<div><b>${p.members}</b><span>${__("Team")}</span></div>
					</div>
					${sprint}
				</div>`);
			$card.on("click keypress", (e) => {
				if (e.type === "keypress" && e.key !== "Enter") return;
				if (p.tracker_identifier) frappe.set_route("project-hub", p.name);
				else frappe.set_route("Form", "Project", p.name);
			});
			$grid.append($card);
		});
	}

	// ------------------------------------------------------------------ one project
	load_project(project) {
		const health = this.view === "health" ? frappe.xcall(`${HUB_API}.get_project_health`, { project, period: ui.getPeriod() }) : null;
		Promise.all([frappe.xcall(`${HUB_API}.get_project_hub`, { project }), health]).then(([data, health_data]) => {
			this.data = data;
			this.project = project;
			const info = data.project;
			this.page.set_title(`${info.project_name || info.name} (${info.tracker_identifier})`);
			this.page.set_indicator(__(info.status), info.status === "Open" ? "blue" : "gray");
			this.setup_actions(data);
			ui.addThemeMenu(this.page, () => this.show(this.route_project, this.view));
			if (this.view === "health") this.render_health(data, health_data);
			else this.render_project(data);
		}).catch((error) => {
			// Only a real access problem is explained to the user; anything else is a bug and must surface.
			if (!(error && String(error.exc_type || error.exc || "").includes("PermissionError"))) throw error;
			this.$body.html(`<div class="text-muted p-4">${__("This project is not available to you.")}</div>`);
		});
	}

	setup_actions(data) {
		const project = this.project;
		const caps = data.capabilities;
		const create = (doctype, extra) => () => frappe.new_doc(doctype, { project, ...(extra || {}) });
		if (caps.can_create_items) this.page.set_primary_action(__("New Work Item"), create("Work Item"), "add");
		this.page.add_inner_button(__("All Projects"), () => frappe.set_route("project-hub"));
		this.page.add_inner_button(this.view === "health" ? __("Overview") : __("Health Dashboard"), () =>
			frappe.set_route("project-hub", project, this.view === "health" ? undefined : "health")
		);
		if (this.view === "health") ui.addPeriodMenu(this.page, () => this.show(this.project, "health"));
		const dash = __("Dashboards");
		this.page.add_inner_button(__("Portfolio"), () => frappe.set_route("portfolio"), dash);
		this.page.add_inner_button(__("My Work"), () => frappe.set_route("my-work"), dash);
		this.page.add_inner_button(__("Quality of this project"), () => {
			frappe.route_options = { project };
			frappe.set_route("quality-dashboard");
		}, dash);
		this.page.add_inner_button(__("Client Status Report"), () => frappe.set_route("status-report", project), dash);
		const view = __("Views");
		const go = (route, options) => () => {
			frappe.route_options = { project, ...options };
			frappe.set_route(...route);
		};
		this.page.add_inner_button(__("Work Items"), go(["List", "Work Item", "List"]), view);
		this.page.add_inner_button(__("Board"), () => window.location.assign(`/desk/work-item/view/kanban/Work%20Items%20by%20Status?project=${encodeURIComponent(project)}`), view);
		this.page.add_inner_button(__("Gantt"), () => window.location.assign(`/desk/work-item/view/gantt?project=${encodeURIComponent(project)}`), view);
		this.page.add_inner_button(__("Calendar"), () => window.location.assign(`/desk/work-item/view/calendar/default?project=${encodeURIComponent(project)}`), view);
		this.page.add_inner_button(__("Sprints"), go(["List", "Sprint", "List"]), view);
		this.page.add_inner_button(__("Releases"), go(["List", "Release", "List"]), view);
		this.page.add_inner_button(__("Time Entries"), go(["List", "Time Entry", "List"]), view);
		const reports = __("Reports");
		["Work Item Summary", "Overdue Work Items", "Client Dependencies", "Time Log Summary", "Release Progress", "Sprint Summary"].forEach((name) => {
			const options = name === "Time Log Summary" ? { project, from_date: frappe.datetime.year_start(), to_date: frappe.datetime.get_today() } : {};
			this.page.add_inner_button(__(name), go(["query-report", name], options), reports);
		});
		if (caps.can_manage_releases) {
			this.page.add_menu_item(__("New Sprint"), create("Sprint"));
			this.page.add_menu_item(__("New Release"), create("Release"));
		}
		if (caps.can_log_time) this.page.add_menu_item(__("Log Time"), create("Time Entry"));
		if (caps.can_manage_categories) this.page.add_menu_item(__("New Category"), create("Work Item Category"));
		this.page.add_menu_item(__("Open Project"), () => frappe.set_route("Form", "Project", project));
	}

	render_project(d) {
		const n = d.numbers;
		const esc = frappe.utils.escape_html;
		const { table, link, stack } = ui;
		const tile = (value, label, cls, route, sub) => ui.tile(value, label, cls, sub, route);
		const waiting_text = (count) => (count ? __("{0} waiting on client", [count]) : "");
		// open tickets split into "with us" and "waiting on client"
		const split = (rows) =>
			stack(rows.map((r) => [__(r.label), r.count - r.client, r.client]), [__("With us"), __("Waiting on client")], ["seg-blue", "seg-orange"]);
		const waiting_panel = `<div class="hub-panel"><h6>${__("Waiting on client")} (${n.client_dependent}) <a class="small" style="float:right" href="#" data-open-report>${__("View all")}</a></h6>${
			d.client_tickets.length
				? table(d.client_tickets, [__("Ticket"), __("Summary"), __("What we need"), __("Waiting")], (t) =>
					`<tr><td style="white-space:nowrap">${link("Work Item", t.name)}</td><td>${esc(t.subject)}</td><td>${esc(t.note || "")}</td><td class="${t.days > 7 ? "text-danger" : ""}" style="white-space:nowrap">${ui.days(t.days)}</td></tr>`)
				: `<div class="text-muted small">${__("Nothing is waiting on the client.")}</div>`
		}</div>`;
		const sprint = d.active_sprint;
		const sprint_html = sprint
			? `<div class="hub-panel"><h6>${__("Active sprint")}: <a href="/desk/sprint/${encodeURIComponent(sprint.name)}">${esc(sprint.sprint_name)}</a></h6>
				<div class="text-muted small">${frappe.datetime.str_to_user(sprint.start_date)} - ${frappe.datetime.str_to_user(sprint.end_date)} · ${sprint.closed_items}/${sprint.total_items} ${__("closed")}</div>
				<div class="progress my-2"><div class="progress-bar" style="width:${flt(sprint.percent_complete)}%"></div></div>
				${sprint.goal ? `<div class="small">${esc(sprint.goal)}</div>` : ""}
				<div class="hub-chart"></div></div>`
			: `<div class="hub-panel"><h6>${__("Active sprint")}</h6><div class="text-muted small">${__("No sprint is running.")}</div></div>`;
		const recent = table(d.recent_items, [__("Item"), __("Subject"), __("Status"), __("Priority"), __("Assigned"), __("Due")], (i) =>
			`<tr><td>${link("Work Item", i.name)}</td><td>${esc(i.subject)}</td><td>${esc(__(i.status))}</td><td>${esc(__(i.priority))}</td><td>${esc(i.assigned_to || "")}</td><td class="${!cint(i.is_closed) && i.due_date && i.due_date < frappe.datetime.get_today() ? "text-danger" : ""}">${i.due_date ? frappe.datetime.str_to_user(i.due_date) : ""}</td></tr>`);
		const sprints = table(d.sprints.slice(0, 6), [__("Sprint"), __("Status"), __("Dates"), __("%")], (s) =>
			`<tr><td>${link("Sprint", s.name, s.sprint_name)}</td><td>${__(s.status)}</td><td>${frappe.datetime.str_to_user(s.start_date)} - ${frappe.datetime.str_to_user(s.end_date)}</td><td>${flt(s.percent_complete, 0)}%</td></tr>`);
		const releases = table(d.releases, [__("Release"), __("Status"), __("Due"), __("%")], (r) =>
			`<tr><td>${link("Release", r.name, r.release_name)}</td><td>${__(r.status)}</td><td>${r.due_date ? frappe.datetime.str_to_user(r.due_date) : ""}</td><td>${flt(r.percent_complete, 0)}%</td></tr>`);
		const team = table(d.members, [__("Name"), __("Role")], (m) => `<tr><td>${esc(m.full_name || m.user)}</td><td>${esc(m.project_role)}</td></tr>`);
		const info = d.project;
		this.$body.html(`
			<div class="hub-title"><h4>${esc(info.project_name || info.name)}</h4>
				<span class="hub-ident">${esc(info.tracker_identifier)}</span>
				<span class="text-muted">${cint(info.is_public) ? __("Public project") : __("Private project")}</span></div>
			<div class="hub-tiles">
				${tile(n.open, __("Open"), "hub-blue", "open", waiting_text(n.client_dependent))}${tile(n.overdue, __("Overdue"), "hub-red", "overdue")}
				${tile(n.mine, __("Assigned to me"), "hub-purple", "mine")}${tile(n.unassigned, __("Unassigned"), "hub-orange", "unassigned")}
				${tile(d.backlog_items, __("Backlog (no sprint)"), "hub-cyan", "backlog", waiting_text(d.backlog_client))}${tile(n.closed, __("Closed"), "hub-green", "closed")}
				${tile(n.client_dependent, __("Waiting on client"), n.client_dependent ? "hub-orange" : "hub-teal", "client", n.client_oldest_days === null || n.client_oldest_days === undefined ? "" : __("oldest {0} days", [n.client_oldest_days]))}
				${tile(n.hours_total, __("Hours logged"), "hub-teal", null, __("{0} h this week", [n.hours_week]))}
			</div>
			<div class="hub-cols">
				<div class="hub-col">
					${sprint_html}
					${waiting_panel}
					<div class="hub-panel"><h6>${__("Recent work items")}</h6>${recent}</div>
				</div>
				<div class="hub-col">
					<div class="hub-panel"><h6>${__("Open by status")}</h6>${split(d.by_status)}<h6 class="mt-3">${__("Open by ticket type")}</h6>${split(d.by_tracker)}</div>
					<div class="hub-panel"><h6>${__("Sprints")}</h6>${sprints}</div>
					<div class="hub-panel"><h6>${__("Releases")}</h6>${releases}</div>
					<div class="hub-panel"><h6>${__("Team")} (${d.members.length})</h6>${team}</div>
				</div>
			</div>`);
		this.$body.find(".hub-tile[data-route]").on("click", (e) => this.open_tile($(e.currentTarget).data("route")));
		this.$body.find("[data-open-report]").on("click", (e) => {
			e.preventDefault();
			this.open_tile("client");
		});
		if (sprint && sprint.burndown.rows.length > 1) {
			const rows = sprint.burndown.rows;
			new frappe.Chart(this.$body.find(".hub-chart")[0], {
				data: {
					labels: rows.map((r) => frappe.datetime.str_to_user(r.date)),
					datasets: [{ name: __("Ideal"), values: rows.map((r) => r.ideal) }, { name: __("Actual"), values: rows.map((r) => r.actual) }],
				},
				type: "line",
				height: 200,
				lineOptions: { hideDots: 1 },
				colors: ["#ec4899", "#2490ef"],
			});
		}
	}

	open_tile(kind) {
		const filters = { project: this.project };
		if (["open", "overdue", "mine", "unassigned", "backlog", "client"].includes(kind)) filters.is_closed = 0;
		if (kind === "client") {
			frappe.route_options = { project: this.project };
			frappe.set_route("query-report", "Client Dependencies");
			return;
		}
		if (kind === "closed") filters.is_closed = 1;
		if (kind === "overdue") filters.due_date = ["<", frappe.datetime.get_today()];
		if (kind === "mine") filters.assigned_to = frappe.session.user;
		if (kind === "unassigned") filters.assigned_to = ["is", "not set"];
		if (kind === "backlog") filters.sprint = ["is", "not set"];
		frappe.route_options = filters;
		frappe.set_route("List", "Work Item", "List");
	}



	chart(selector, config) {
		ui.chart(this.$body, selector, config);
	}

	render_health(d, h) {
		const esc = frappe.utils.escape_html;
		const info = d.project;
		const f = h.flow;
		const t = h.time;
		const st = h.status;
		const per = h.bucket === "month" ? __("monthly") : __("weekly");
		const { bar, stack, panel, table, link } = ui;
		const split = (rows) =>
			stack(rows.map((r) => [__(r.label), r.count - r.client, r.client]), [__("With us"), __("Waiting on client")], ["seg-blue", "seg-orange"]);
		const waiting_panel = panel(
			`${__("Waiting on client")} (${f.client_dependent}) <a class="small" style="float:right" href="#" data-open-report>${__("View all")}</a>`,
			d.client_tickets.length
				? table(d.client_tickets, [__("Ticket"), __("Summary"), __("What we need"), __("Waiting")], (t) =>
					`<tr><td style="white-space:nowrap">${link("Work Item", t.name)}</td><td>${esc(t.subject)}</td><td>${esc(t.note || "")}</td><td class="${t.days > 7 ? "text-danger" : ""}" style="white-space:nowrap">${ui.days(t.days)}</td></tr>`)
				: `<div class="text-muted small">${__("Nothing is waiting on the client.")}</div>`
		);
		const tile = (value, label, cls, sub) =>
			`<div class="hub-tile ${cls || ""}"><b>${value}</b><span>${label}</span>${sub ? `<em>${sub}</em>` : ""}</div>`;
		const risk_badge = (r) => `<span class="hub-badge hub-risk-${r.risk}">${r.risk === "late" ? __("Late") : r.risk === "risk" ? __("At Risk") : __("On Track")}</span>`;
		const releases = h.releases.length
			? `<table class="table table-sm hub-table"><thead><tr><th>${__("Release")}</th><th>${__("Due")}</th><th>${__("Days left")}</th><th>${__("Progress")}</th><th></th></tr></thead><tbody>${h.releases
					.map(
						(r) => `<tr><td>${esc(r.label)}</td><td>${r.due_date ? frappe.datetime.str_to_user(r.due_date) : ""}</td><td>${r.days_left === null ? "" : r.days_left}</td>
						<td style="min-width:120px"><div class="progress"><div class="progress-bar" style="width:${flt(r.percent)}%"></div></div></td><td>${risk_badge(r)}</td></tr>`
					)
					.join("")}</tbody></table>`
			: `<div class="text-muted small">${__("No open releases")}</div>`;
		const hours_max = Math.max(t.estimated, t.spent, 1);
		const pct = (n) => (f.total ? (n / f.total) * 100 : 0);
		const with_us = f.open - f.client_dependent;
		const open_closed = `<div class="hub-meter"><i class="seg-blue" style="width:${pct(with_us)}%">${with_us}</i><i class="seg-orange" style="width:${pct(f.client_dependent)}%">${f.client_dependent || ""}</i><i class="seg-green" style="width:${pct(f.closed)}%">${f.closed}</i></div>` +
			stack(f.by_tracker.map((r) => [__(r.label), r.open, r.client, r.closed]), [__("Open (with us)"), __("Waiting on client"), __("Closed")], ["seg-blue", "seg-orange", "seg-green"]);
		const people_panels =
			panel(__("Open tickets by person"), h.workload.length ? h.workload.map((w) => bar(w.name, w.open, Math.max(...h.workload.map((x) => x.open)))).join("") : `<div class="text-muted small">${__("Nothing open")}</div>`) +
			  panel(__("Hours by person (billable vs non-billable)"), stack(t.by_user.map((u) => [u.name, u.billable, u.non_billable]), [__("Billable"), __("Non-billable")], ["seg-green", "seg-orange"]));

		this.$body.html(`
			<div class="hub-title"><h4>${esc(info.project_name || info.name)}</h4><span class="hub-ident">${esc(info.tracker_identifier)}</span>
				<span class="text-muted">${__("Project health")} · ${__(ui.PERIOD_NOTE[h.period])} · ${frappe.datetime.str_to_user(frappe.datetime.get_today())}</span></div>
			${st ? ui.statusBanner(st) : ""}
			<div class="hub-tiles">
				${tile(`${f.completion_pct}%`, __("Complete"), "hub-green", __("{0} of {1} tickets", [f.closed, f.total]))}
				${tile(f.open, __("Open tickets"), "hub-blue", `${f.client_dependent ? `${__("{0} waiting on client", [f.client_dependent])} · ` : ""}${__("{0} h estimated", [f.estimated_open_hours])}`)}
				${tile(f.closed, __("Closed tickets"), "hub-green", __("{0} h estimated", [f.estimated_closed_hours]))}
				${tile(`${f.overdue_pct}%`, __("Open & overdue"), f.overdue ? "hub-red" : "hub-teal", __("{0} tickets", [f.overdue]))}
				${tile(f.client_dependent, __("Waiting on client"), f.client_dependent ? "hub-orange" : "hub-teal", f.client_oldest_days === null ? "" : __("oldest {0} days", [f.client_oldest_days]))}
				${tile(t.spent, __("Hours spent"), "hub-cyan", t.burn_pct === null ? "" : __("{0}% of estimate", [t.burn_pct]))}
				${tile(t.billable, __("Billable hours"), "hub-teal", __("{0}% of spent", [t.billable_pct]))}
				${tile(t.non_billable, __("Non-billable hours"), "hub-orange")}
			</div>
			<div class="hub-cols hub-cols-even">
				<div class="hub-col">
					${panel(`${__("Tickets created vs resolved")} (${per})`, `<div class="hub-chart" id="hc-flow"></div><div class="small text-muted mt-2">${__("{0} created · {1} resolved in this range", [f.created_total, f.resolved_total]) + (f.created_waiting ? ` · ${__("{0} of the new tickets are waiting on the client", [f.created_waiting])}` : "")}</div>`)}
					${panel(__("Open vs closed (by type)"), open_closed)}
					${panel(`${__("Spent time: billable vs non-billable")} (${per})`, `<div class="hub-chart" id="hc-time"></div>`)}
					${panel(__("Hours by activity (billable vs non-billable)"), stack(t.by_activity.map((a) => [a.label, a.billable, a.non_billable]), [__("Billable"), __("Non-billable")], ["seg-green", "seg-orange"]))}
					${people_panels}
				</div>
				<div class="hub-col">
					${panel(`${__("Open backlog trend")} (${per})`, `<div class="hub-chart" id="hc-trend"></div>`)}
					${panel(__("Open by status (with us vs waiting on client)"), split(f.open_by_status))}
					${waiting_panel}
					${panel(__("Estimated vs spent hours"), `${bar(__("Estimated"), t.estimated, hours_max)}${bar(__("Spent"), t.spent, hours_max)}${bar(__("Billable"), t.billable, hours_max)}${bar(__("Non-billable"), t.non_billable, hours_max)}`)}
					${panel(__("Sprint velocity (tickets closed per completed sprint)"), h.velocity.length ? `<div class="hub-chart" id="hc-velocity"></div><div class="small text-muted mt-2">${__("Average {0} tickets / {1} hours per sprint", [flt(h.velocity.reduce((a, v) => a + v.items, 0) / h.velocity.length, 1), flt(h.velocity.reduce((a, v) => a + v.hours, 0) / h.velocity.length, 1)])}</div>` : `<div class="text-muted small">${__("No completed sprints yet")}</div>`)}
					${panel(__("Age of open tickets"), `<div class="hub-chart" id="hc-aging"></div>`)}
					${panel(__("Open tickets by priority"), split(f.open_by_priority))}
					${panel(__("Releases"), releases)}
				</div>
			</div>`);

		this.$body.find("[data-open-report]").on("click", (e) => {
			e.preventDefault();
			this.open_tile("client");
		});
		const weeks = h.labels;
		const palette = { blue: "#3b82f6", green: "#10b981", orange: "#f59e0b", purple: "#8b5cf6", cyan: "#06b6d4", red: "#ef4444", pink: "#ec4899" };
		this.chart("#hc-flow", { type: "bar", data: { labels: weeks, datasets: [{ name: __("Created"), values: f.created }, { name: __("Resolved"), values: f.resolved }] }, colors: [palette.blue, palette.green], barOptions: { spaceRatio: 0.4 } });
		this.chart("#hc-trend", { type: "line", data: { labels: weeks, datasets: [{ name: __("Open tickets"), values: f.open_trend }, { name: __("of which waiting on client"), values: f.client_trend }] }, colors: [palette.purple, palette.orange], lineOptions: { regionFill: 1 } });
		this.chart("#hc-time", { type: "bar", data: { labels: weeks, datasets: [{ name: __("Billable"), values: t.billable_by_week }, { name: __("Non-billable"), values: t.non_billable_by_week }] }, colors: [palette.green, palette.orange], barOptions: { stacked: 1, spaceRatio: 0.4 } });
		if (h.velocity.length) this.chart("#hc-velocity", { type: "bar", data: { labels: h.velocity.map((v) => v.sprint), datasets: [{ name: __("Tickets closed"), values: h.velocity.map((v) => v.items) }] }, colors: [palette.purple], barOptions: { spaceRatio: 0.5 } });
		this.chart("#hc-aging", { type: "bar", data: { labels: f.aging.map((a) => a.label), datasets: [{ name: __("With us"), values: f.aging.map((a) => a.count - a.client) }, { name: __("Waiting on client"), values: f.aging.map((a) => a.client) }] }, colors: [palette.blue, palette.orange], barOptions: { stacked: 1, spaceRatio: 0.5 } });
	}




}
