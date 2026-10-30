// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// Project Hub: pick a project, then work inside it (tickets, board, sprints, releases, team, time, reports).
const HUB_API = "auri_pms.auri_pms.api";

/* global auri_pms */
let ui; // shared UI kit, available once auri_hub.bundle.js has loaded

frappe.pages["project-hub"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Project Hub"), single_column: true });
	frappe.require("auri_hub.bundle.js", () => {
		ui = auri_pms.ui;
		wrapper.project_hub = new ProjectHub(page, wrapper);
		const route = frappe.get_route();
		wrapper.project_hub.show(route[1], route[2], route[3]);
	});
};

frappe.pages["project-hub"].on_page_show = function (wrapper) {
	if (!wrapper.project_hub) return; // the first render happens when the bundle has loaded
	const route = frappe.get_route();
	wrapper.project_hub.show(route[1], route[2], route[3]);
};

class ProjectHub {
	constructor(page, wrapper) {
		this.page = page;
		this.$body = $(`<div class="auri-hub"></div>`).appendTo(page.main);
		ui.injectStyle();
		ui.applyTheme(this.$body);
	}

	show(project, view, snapshot) {
		this.view = ["health", "history"].includes(view) ? view : "overview";
		this.snapshot = this.view === "history" && snapshot ? decodeURIComponent(snapshot) : null;
		ui.showSidebar();
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
		this.pick = { query: "", filter: "all" };
		frappe.xcall(`${HUB_API}.get_hub_projects`).then((projects) => {
			this.projects = projects;
			const sum = (key) => projects.reduce((t, p) => t + cint(p[key]), 0);
			const stat = (value, label, tone) => `<div class="pk-stat ${tone || ""}"><b>${value}</b><span>${label}</span></div>`;
			this.$body.html(`<div class="ph2 pk">
				<div class="hub-title"><h4>${__("Project Hub")}</h4><span class="text-muted">${frappe.datetime.str_to_user(frappe.datetime.get_today())}</span></div>
				<div class="pk-summary">
					${stat(projects.length, __("Projects"), "pk-acc")}${stat(sum("open"), __("Open tickets"))}${stat(sum("overdue"), __("Overdue"), sum("overdue") ? "pk-bad" : "")}${stat(sum("mine"), __("Assigned to me"))}
				</div>
				<div class="pk-toolbar">
					<div class="pk-search"><input type="text" class="form-control" placeholder="${__("Search projects")}"></div>
					<div class="pk-chips">${[["all", __("All")], ["mine", __("My tickets")], ["overdue", __("Overdue")]].map(([key, text]) => `<span class="pk-chip ${key === "all" ? "active" : ""}" data-filter="${key}">${text}</span>`).join("")}</div>
				</div>
				<div class="pk-grid"></div></div>`);
			this.$body.find(".pk-search input").on("input", (e) => {
				this.pick.query = $(e.target).val();
				this.render_cards();
			});
			this.$body.find(".pk-chip").on("click", (e) => {
				this.pick.filter = $(e.currentTarget).data("filter");
				this.$body.find(".pk-chip").each((_i, el) => $(el).toggleClass("active", $(el).data("filter") === this.pick.filter));
				this.render_cards();
			});
			this.render_cards();
			if (frappe.boot.auri_pms_portfolio) this.page.add_inner_button(__("Delivery & Health"), () => frappe.set_route("management-dashboard"));
			this.page.add_inner_button(__("My Work"), () => frappe.set_route("my-work"));
			this.page.add_inner_button(__("Quality"), () => frappe.set_route("quality-dashboard"));
			ui.addThemeMenu(this.page, () => this.show(this.route_project, this.view, this.snapshot));
		});
	}

	render_cards() {
		const esc = frappe.utils.escape_html;
		const q = this.pick.query.toLowerCase();
		const today = frappe.datetime.get_today();
		const rows = this.projects.filter((p) =>
			`${p.project_name} ${p.tracker_identifier || ""}`.toLowerCase().includes(q) &&
			(this.pick.filter === "all" || (this.pick.filter === "mine" ? p.mine : p.overdue))
		);
		const $grid = this.$body.find(".pk-grid").empty();
		if (!rows.length) {
			$grid.html(`<div class="hub-panel ph2-empty">${this.projects.length ? __("No project matches.") : __("No projects found. Ask a project manager to add you as a member.")}</div>`);
			return;
		}
		rows.forEach((p, k) => {
			const total = cint(p.total);
			const done = total ? Math.round((p.closed / total) * 100) : 0;
			const on_time = Math.max(0, p.open - p.overdue);
			let days = "";
			if (p.expected_end_date) {
				const left = frappe.datetime.get_diff(p.expected_end_date, today);
				days = `<span class="pk-days ${left < 0 ? "pk-late" : left <= 14 ? "pk-soon" : ""}">${left < 0 ? __("{0}d over", [-left]) : __("{0}d left", [left])}</span>`;
			}
			const sprint = p.active_sprint
				? `<div class="pk-sprint"><span>${esc(p.active_sprint.sprint_name || p.active_sprint.name)}</span><div class="pk-track"><i style="--w:${flt(p.active_sprint.percent_complete)}%"></i></div><b>${Math.round(flt(p.active_sprint.percent_complete))}%</b></div>`
				: `<div class="pk-sprint pk-nosprint">${__("No active sprint")}</div>`;
			const bar = total
				? `<div class="pk-split" title="${__("{0} closed · {1} open · {2} overdue", [p.closed, on_time, p.overdue])}"><i class="pk-closed" style="flex:${p.closed}"></i><i class="pk-open" style="flex:${on_time}"></i><i class="pk-over" style="flex:${p.overdue}"></i></div>`
				: `<div class="pk-split pk-empty"></div>`;
			const $card = $(`
				<div class="hub-panel pk-card ph2-in" tabindex="0" style="animation-delay:${k * 30}ms">
					<div class="pk-top">
						<div class="pk-ring" style="--p:${done}"><svg viewBox="0 0 44 44"><circle cx="22" cy="22" r="18" class="pk-ring-bg"/><circle cx="22" cy="22" r="18" class="pk-ring-fg" pathLength="100"/></svg><b>${done}<small>%</small></b></div>
						<div class="pk-name"><b>${esc(p.project_name || p.name)}</b>
							<small>${p.tracker_identifier ? `<span class="pk-ident">${esc(p.tracker_identifier)}</span>` : `<span class="pk-ident pk-warn">${__("No identifier")}</span>`}${cint(p.is_public) ? __("Public") : __("Private")}</small></div>
						${days}
					</div>
					${bar}
					<div class="pk-nums">
						<div><b>${p.open}</b><span>${__("Open")}</span></div>
						<div class="${p.overdue ? "pk-bad" : ""}"><b>${p.overdue}</b><span>${__("Overdue")}</span></div>
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
			ui.addThemeMenu(this.page, () => this.show(this.route_project, this.view, this.snapshot));
			if (this.view === "health") this.render_health(data, health_data);
			else if (this.view === "history") return this.render_history(data);
			else this.render_project(data);
			this.add_tabs();
		}).catch((error) => {
			// Only a real access problem is explained to the user; anything else is a bug and must surface.
			if (!(error && String(error.exc_type || error.exc || "").includes("PermissionError"))) throw error;
			this.$body.html(`<div class="text-muted p-4">${__("This project is not available to you.")}</div>`);
		});
	}

	// ------------------------------------------------------------------ project tabs
	add_tabs(note) {
		const project = encodeURIComponent(this.project);
		const base = window.location.pathname.split("/project-hub")[0] + "/project-hub"; // keeps a /desk/auri-pms prefix
		const tab = (key, label, route) => `<a class="pt-tab ${this.view === key ? "pt-on" : ""}" href="${base}/${project}${route}">${label}</a>`;
		const open = (label, doctype) => `<a class="pt-tab pt-link" href="#" data-pt-list="${doctype}">${label} <span>↗</span></a>`;
		const $tabs = $(`<nav class="pt-tabs">${tab("overview", __("Overview"), "")}${tab("health", __("Health"), "/health")}${tab("history", __("History"), "/history")}
			<i></i>${open(__("Tickets"), "Work Item")}${open(__("Releases"), "Release")}${open(__("Sprints"), "Sprint")}${open(__("Risks"), "Risk Register")}${open(__("Time"), "Time Entry")}</nav>${note || ""}`);
		$tabs.filter("nav").find("[data-pt-list]").on("click", (e) => {
			e.preventDefault();
			frappe.route_options = { project: this.project };
			frappe.set_route("List", $(e.currentTarget).data("pt-list"), "List");
		});
		this.$body.prepend($tabs);
	}

	// ------------------------------------------------------------------ history: saved dashboards of this project
	render_history(data) {
		if (this.snapshot) return this.render_saved(data);
		if (data.capabilities.can_create_items) {
			this.page.set_primary_action(__("Save snapshot"), () =>
				frappe.xcall("auri_pms.auri_pms.snapshots.take_project_snapshot", { project: this.project }).then(() => {
					frappe.show_alert({ message: __("Dashboard saved"), indicator: "green" });
					this.show(this.project, "history");
				}), "add");
		}
		frappe.xcall("auri_pms.auri_pms.snapshots.get_project_snapshots", { project: this.project }).then((rows) => {
			const esc = frappe.utils.escape_html;
			const tone = (label) => (label === "On Track" ? "ok" : label === "At Risk" ? "warn" : label ? "bad" : "");
			const diff = (now, before, good_down) => {
				if (before === undefined || now === before) return "";
				const up = now > before;
				return `<em class="ph-d ${up === !good_down ? "ph-good" : "ph-bad"}">${up ? "▲" : "▼"} ${Math.abs(flt(now - before, 1))}</em>`;
			};
			const [last, prev] = rows;
			const card = (label, key, good_down, unit) => `<div class="hist-card"><span>${label}</span><b>${last ? flt(last[key], key.includes("pct") || key.includes("hours") ? 1 : 0) : "–"}${unit || ""}</b>${last ? diff(last[key], prev && prev[key], good_down) : ""}</div>`;
			const ordered = [...rows].reverse();
			this.$body.html(`<div class="ph2 hist">
				<div class="hub-title"><h4>${__("History")}</h4><span class="text-muted">${__("Saved dashboards of this project: every Monday, on the 1st of each month, and whenever you press Save snapshot.")}</span></div>
				${rows.length ? `<div class="hist-cards">${card(__("Health score"), "health_score")}${card(__("Complete"), "completion_pct", false, "%")}${card(__("Open tickets"), "open_tickets", true)}${card(__("Overdue"), "overdue_tickets", true)}${card(__("Hours spent"), "spent_hours")}${card(__("Open risks"), "open_risks", true)}</div>
				<div class="hub-panel ph2-card"><div class="ph2-card-head"><h6>${__("Trend")}</h6></div>${rows.length > 1 ? '<div class="hub-chart" id="hc-hist"></div>' : `<div class="ph2-empty">${__("The trend appears once two dashboards are saved.")}</div>`}</div>
				<div class="hub-panel ph2-card"><div class="ph2-card-head"><h6>${__("Saved dashboards")}</h6><span class="text-muted small">${rows.length}</span></div>
				<table class="hist-table"><thead><tr><th>${__("Date")}</th><th>${__("Type")}</th><th>${__("Health")}</th><th>${__("Score")}</th><th>${__("Complete")}</th><th>${__("Open")}</th><th>${__("Overdue")}</th><th>${__("Hours")}</th><th></th></tr></thead><tbody>
				${rows.map((r) => `<tr data-snap="${esc(r.name)}"><td>${frappe.datetime.str_to_user(r.snapshot_date)}</td><td>${__(r.period_type)}</td><td><span class="hub-badge pt-${tone(r.health_label)}">${esc(r.health_label || "–")}</span></td><td>${r.health_score}</td><td>${flt(r.completion_pct, 0)}%</td><td>${r.open_tickets}</td><td>${r.overdue_tickets}</td><td>${flt(r.spent_hours, 1)}</td><td class="text-right"><a href="${window.location.pathname.split("/project-hub")[0]}/project-hub/${encodeURIComponent(this.project)}/history/${encodeURIComponent(r.name)}">${__("Open")} →</a>${r.can_delete ? ` <a href="#" class="hist-del" data-del="${esc(r.name)}" title="${__("Delete this saved dashboard")}">${__("Delete")}</a>` : ""}</td></tr>`).join("")}
				</tbody></table></div>`
				: `<div class="hub-panel ph2-card"><div class="ph2-empty">${__("No dashboards saved yet. Press Save snapshot to keep today's figures; later ones will be added every Monday and on the 1st of each month.")}</div></div>`}
			</div>`);
			this.$body.find("[data-del]").on("click", (e) => {
				e.preventDefault();
				const name = $(e.currentTarget).data("del");
				frappe.confirm(__("Delete the saved dashboard {0}? This cannot be undone.", [name]), () =>
					frappe.xcall("auri_pms.auri_pms.snapshots.delete_project_snapshot", { name }).then(() => {
						frappe.show_alert({ message: __("Deleted"), indicator: "green" });
						this.show(this.project, "history");
					})
				);
			});
			if (rows.length > 1) {
				this.chart("#hc-hist", { type: "line", height: 200, data: { labels: ordered.map((r) => frappe.datetime.str_to_user(r.snapshot_date)), datasets: [{ name: __("Health score"), values: ordered.map((r) => r.health_score) }, { name: __("Open tickets"), values: ordered.map((r) => r.open_tickets) }, { name: __("Complete %"), values: ordered.map((r) => flt(r.completion_pct, 0)) }] }, colors: ["#8b5cf6", "#f59e0b", "#10b981"], axisOptions: { xIsSeries: 1 } });
			}
			this.add_tabs();
		});
	}

	// one saved dashboard, shown with the Health layout and a banner that says it is a record
	render_saved(data) {
		frappe.xcall("auri_pms.auri_pms.snapshots.get_project_snapshot", { name: this.snapshot }).then((snap) => {
			this.render_health(data, snap.data);
			const when = frappe.datetime.str_to_user(snap.snapshot_date);
			this.add_tabs(`<div class="pt-banner">${__("Saved dashboard of {0} ({1}). Figures are as they were on that day.", [when, __(snap.period_type)])} <a href="${window.location.pathname.split("/project-hub")[0]}/project-hub/${encodeURIComponent(this.project)}/history">← ${__("Back to history")}</a></div>`);
		});
	}

	setup_actions(data) {
		const project = this.project;
		const caps = data.capabilities;
		const create = (doctype, extra) => () => frappe.new_doc(doctype, { project, ...(extra || {}) });
		if (caps.can_create_items) this.page.set_primary_action(__("New Work Item"), create("Work Item"), "add");
		this.page.add_inner_button(__("All Projects"), () => frappe.set_route("project-hub"));
		if (this.view === "health") ui.addPeriodMenu(this.page, () => this.show(this.project, "health"));
		const dash = __("Dashboards");
		if (frappe.boot.auri_pms_portfolio) this.page.add_inner_button(__("Delivery & Health"), () => frappe.set_route("management-dashboard"), dash);
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
		this.page.add_inner_button(__("Risk Register"), () => window.location.assign(`/desk/risk-register?project=${encodeURIComponent(project)}`), view);
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
		const info = d.project;
		const today = frappe.datetime.get_today();
		const days_to = (date) => frappe.datetime.get_diff(date, today);
		const initials = (name) => esc(String(name || "?").split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join(""));
		const items = (filters) => ui.go("Work Item", { project: this.project, ...filters });
		const clamp = (v) => Math.max(0, Math.min(100, Math.round(v)));

		// ---- header: name, identifier, status, and the project's own timeline
		let schedule = null;
		let timeline = "";
		if (info.expected_start_date && info.expected_end_date) {
			const span = Math.max(frappe.datetime.get_diff(info.expected_end_date, info.expected_start_date), 1);
			schedule = clamp((frappe.datetime.get_diff(today, info.expected_start_date) / span) * 100);
			const left = days_to(info.expected_end_date);
			timeline = `<div class="ph3-tl">
				<span>${frappe.datetime.str_to_user(info.expected_start_date)}</span>
				<div class="ph2-tl-track"><i style="--w:${schedule}%"></i><em style="left:${schedule}%"></em></div>
				<span>${frappe.datetime.str_to_user(info.expected_end_date)}</span>
				<b class="${left < 0 ? "ph2-bad" : ""}">${left < 0 ? __("{0}d over", [-left]) : __("{0}d left", [left])}</b></div>`;
		}
		const header = `<div class="hub-title"><h4>${esc(info.project_name || info.name)}</h4>
				<span class="hub-ident">${esc(info.tracker_identifier)}</span>
				<span class="text-muted">${cint(info.is_public) ? __("Public project") : __("Private project")}</span>${ui.projectDates(info)}</div>`;

		// ---- four rings: done, time elapsed, hours used, sprint
		const ring = (value, label, sub, tone, target) => `<div class="hub-panel ph3-gauge ph2-in" ${target ? ui.goAttr(target) : ""}>
			<div class="ph2-ring ph3-ring ${tone || ""}" style="--p:${value === null ? 0 : value}">
				<svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="ph2-ring-bg"/><circle cx="60" cy="60" r="52" class="ph2-ring-fg" pathLength="100"/></svg>
				<div><div class="ph2-ring-num"><b data-count="${value === null ? 0 : value}">${value === null ? "–" : 0}</b>${value === null ? "" : "<span>%</span>"}</div></div>
			</div><strong>${label}</strong><small>${sub || ""}</small></div>`;
		const done = n.total ? clamp((n.closed / n.total) * 100) : 0;
		const hours_basis = n.hours_budget || n.hours_estimated; // a project budget replaces the ticket estimates
		const burn = hours_basis ? clamp((n.hours_total / hours_basis) * 100) : null;
		const sp = d.active_sprint;
		const gauges = `<div class="ph3-gauges">
			${ring(done, __("Complete"), `${n.closed} / ${n.total}`, "g-green", items({}))}
			${ring(schedule, __("Time elapsed"), schedule === null ? __("no dates") : days_to(info.expected_end_date) < 0 ? __("{0} days over", [-days_to(info.expected_end_date)]) : __("{0} days left", [days_to(info.expected_end_date)]), schedule !== null && schedule > done + 20 ? "g-orange" : "g-blue")}
			${ring(burn, __("Hours used"), `${flt(n.hours_total, 0)} / ${flt(hours_basis, 0)} h${n.hours_budget ? ` ${__("budget")}` : ""}`, burn !== null && burn > 100 ? "g-red" : "g-teal", ui.go("Time Entry", { project: this.project }))}
			${ring(sp ? clamp(sp.percent_complete) : null, __("Sprint"), sp ? esc(sp.sprint_name) : __("none running"), sp && days_to(sp.end_date) < 0 ? "g-orange" : "g-purple", sp ? { route: ["Form", "Sprint", sp.name], filters: {} } : null)}
		</div>`;

		// ---- numbers: the theme's coloured tiles
		const tile = (value, label, cls, route, sub) => ui.tile(value, label, cls, sub, route);
		const kpis = `<div class="hub-tiles">
				${tile(n.open, __("Open"), "hub-blue", "open", n.client_dependent ? __("{0} waiting on client", [n.client_dependent]) : "")}${tile(n.overdue, __("Overdue"), "hub-red", "overdue")}
				${tile(n.mine, __("Assigned to me"), "hub-purple", "mine")}${tile(n.unassigned, __("Unassigned"), "hub-orange", "unassigned")}
				${tile(d.backlog_items, __("Backlog (no sprint)"), "hub-cyan", "backlog")}${tile(n.closed, __("Closed"), "hub-green", "closed")}
				${tile(n.client_dependent, __("Waiting on client"), n.client_dependent ? "hub-orange" : "hub-teal", "client", n.client_oldest_days ? __("oldest {0} days", [n.client_oldest_days]) : "")}
				${tile(n.hours_total, __("Hours logged"), "hub-teal", ui.go("Time Entry", { project: this.project }), __("{0} h this week", [n.hours_week]))}
			</div>`;

		// ---- tickets: a column per status (open statuses then closed) and the open tickets by priority; every part opens its list
		const segs = [...d.by_status.map((r) => ({ label: __(r.label), value: r.count, target: items({ is_closed: 0, status: r.label }) })),
			{ label: __("Closed"), value: n.closed, target: items({ is_closed: 1 }), closed: true }].filter((s) => s.value);
		const hues = ["#6366f1", "#8b5cf6", "#06b6d4", "#f59e0b", "#ec4899", "#64748b"];
		const seg_total = segs.reduce((t, s) => t + s.value, 0) || 1;
		const seg_max = Math.max(1, ...segs.map((s) => s.value));
		segs.forEach((s, k) => (s.colour = s.closed ? "#10b981" : hues[k % hues.length]));
		const PRIORITY = { Urgent: "#ef4444", High: "#f97316", Medium: "#6366f1", Normal: "#6366f1", Low: "#94a3b8" };
		const prio = d.by_priority || [];
		const prio_open = prio.reduce((t, p) => t + p.count, 0) || 1;
		const tickets = `<div class="hub-panel ph2-card ph2-in tk">
			<div class="ph2-card-head"><h6>${__("Tickets")}</h6>${ui.viewAll(items({}))}</div>
			<div class="ph3-tk-head"><b data-count="${n.total}">0</b><span>${__("tickets")} · ${__("{0} open", [n.open])}</span><em>${__("{0}% closed", [Math.round(done)])}</em></div>
			${segs.length ? `<div class="tk-cols">${segs.map((s) => `<div class="tk-col" style="--c:${s.colour};--h:${(s.value / seg_max) * 100}%" ${ui.goAttr(s.target)} title="${esc(s.label)}: ${s.value}">
					<b>${s.value}</b><div class="tk-col-bar"><i></i></div><span>${esc(s.label)}</span><small>${Math.round((s.value / seg_total) * 100)}%</small></div>`).join("")}</div>`
				: `<div class="ph2-empty">${__("No tickets yet")}</div>`}
			${prio.length ? `<div class="tk-prio"><div class="tk-prio-head">${__("Open by priority")}</div>
				<div class="tk-prio-bar">${prio.map((p) => `<i style="flex:${p.count};background:${PRIORITY[p.label] || "#64748b"}" ${ui.goAttr(items({ is_closed: 0, priority: p.label }))} title="${esc(__(p.label))}: ${p.count}"></i>`).join("")}</div>
				<div class="tk-prio-keys">${prio.map((p) => `<span ${ui.goAttr(items({ is_closed: 0, priority: p.label }))}><i style="background:${PRIORITY[p.label] || "#64748b"}"></i>${esc(__(p.label))}<b>${p.count}</b><small>${Math.round((p.count / prio_open) * 100)}%</small></span>`).join("")}</div></div>` : ""}
		</div>`;

		// ---- workload: assigned / overdue / unassigned, then open tickets per person with the overdue part in red
		const people = (d.by_assignee || []).slice(0, 6);
		const most = Math.max(1, n.unassigned, ...people.map((p) => p.open));
		const assigned = n.open - n.unassigned;
		const wl_stat = (label, value, tone, target) => `<div class="wl-stat wl-${tone}" ${ui.goAttr(target)}><b>${value}</b><span>${label}</span></div>`;
		const wl_row = (avatar, name, open, overdue, target, warn) => `<div class="wl-row" ${ui.goAttr(target)} title="${esc(name)}: ${open} ${__("open")}, ${overdue} ${__("overdue")}">
			${avatar}<div class="wl-who"><b>${esc(name)}</b><small>${warn ? __("need an owner") : overdue ? __("{0} open · {1} overdue", [open, overdue]) : __("{0} open", [open])}</small></div>
			<div class="wl-bar">${warn ? `<i class="wl-warn" style="--w:${(open / most) * 100}%"></i>` : `<i class="wl-ok" style="--w:${((open - overdue) / most) * 100}%"></i><i class="wl-bad" style="--w:${(overdue / most) * 100}%"></i>`}</div>
			<em>${open}</em></div>`;
		const workload = `<div class="hub-panel ph2-card ph2-in wl">
			<div class="ph2-card-head"><h6>${__("Workload")}</h6><span class="ph2-sub">· ${__("{0} people", [(d.by_assignee || []).length])}</span>${ui.viewAll(items({ is_closed: 0 }))}</div>
			<div class="wl-stats">
				${wl_stat(__("Assigned"), assigned, "acc", items({ is_closed: 0, assigned_to: ["is", "set"] }))}
				${wl_stat(__("Overdue"), n.overdue, n.overdue ? "bad" : "ok", items({ is_closed: 0, due_date: ["<", today] }))}
				${wl_stat(__("Unassigned"), n.unassigned, n.unassigned ? "warn" : "ok", items({ is_closed: 0, assigned_to: ["is", "not set"] }))}
			</div>
			<div class="wl-list">
				${people.map((p) => wl_row(`<span class="ph2-avatar">${initials(p.name)}</span>`, p.name, p.open, p.overdue, items({ is_closed: 0, assigned_to: p.user }))).join("")}
				${n.unassigned ? wl_row(`<span class="ph2-avatar ph2-avatar-empty">?</span>`, __("Unassigned"), n.unassigned, 0, items({ is_closed: 0, assigned_to: ["is", "not set"] }), true) : ""}
				${!people.length && !n.unassigned ? `<div class="ph2-empty">${__("Nothing open")}</div>` : ""}
			</div>
			${(d.by_assignee || []).length > people.length ? `<div class="wl-more">${__("+ {0} more", [(d.by_assignee || []).length - people.length])}</div>` : ""}
		</div>`;

		// ---- tickets created, moved to Resolved and closed per week (last 3 months)
		const fl = d.flow;
		const since = fl.starts[0];
		const sum = (list) => list.reduce((t, v) => t + v, 0);
		const net = sum(fl.created) - sum(fl.closed);
		const flow_stat = (label, value, colour, target, sub) => `<div class="fl-stat" ${target ? ui.goAttr(target) : ""}><span><i style="background:${colour}"></i>${label}</span><b>${value}</b>${sub ? `<small>${sub}</small>` : ""}</div>`;
		const flow_card = `<div class="hub-panel ph2-card ph2-in fl">
			<div class="ph2-card-head"><h6>${__("Tickets created vs resolved vs closed")}</h6><span class="ph2-sub">· ${__("weekly, last 3 months")}</span>${ui.viewAll(items({ creation: [">=", since] }))}</div>
			<div class="fl-body">
				<div class="fl-stats">
					${flow_stat(__("Created"), sum(fl.created), "#6366f1", items({ creation: [">=", since] }))}
					${flow_stat(__("Resolved"), sum(fl.resolved), "#06b6d4", items({ status: "Resolved" }), __("moved to Resolved"))}
					${flow_stat(__("Closed"), sum(fl.closed), "#10b981", items({ is_closed: 1, closed_on: [">=", since] }))}
					${flow_stat(__("Backlog change"), `${net > 0 ? "+" : ""}${net}`, net > 0 ? "#ef4444" : "#10b981", null, net > 0 ? __("more created than closed") : __("closed at least as many as created"))}
				</div>
				<div class="fl-chart">${this.flow_chart(fl, items)}</div>
			</div></div>`;

		// ---- risks: open count, split by level and the probability x impact matrix
		const rk = d.risks;
		const risk_list = (filters) => ui.go("Risk Register", { project: this.project, ...filters });
		const LEVEL = { Critical: "#ef4444", High: "#f97316", Medium: "#eab308", Low: "#10b981" };
		const levels = Object.keys(LEVEL).filter((l) => cint(rk.by_level[l]));
		const risks = `<div class="hub-panel ph2-card ph2-in rk">
			<div class="ph2-card-head"><h6>${__("Risks")}</h6>${ui.viewAll(risk_list({}))}</div>
			${rk.total ? `<div class="rk-head"><b data-count="${rk.open}">0</b><span>${__("open risks")}</span>
					${rk.overdue ? `<em ${ui.goAttr(risk_list({ status: ["in", ui.OPEN_RISK], mitigation_due: ["<", frappe.datetime.get_today()] }))}>${__("{0} past mitigation date", [rk.overdue])}</em>` : ""}</div>
				<div class="rk-bar">${levels.map((l) => `<i style="flex:${rk.by_level[l]};background:${LEVEL[l]}" ${ui.goAttr(risk_list({ risk_level: l, status: ["in", ui.OPEN_RISK] }))} title="${__(l)}: ${rk.by_level[l]}"></i>`).join("") || "<i class='rk-none'></i>"}</div>
				<div class="rk-keys">${Object.keys(LEVEL).map((l) => `<span class="${cint(rk.by_level[l]) ? "" : "rk-zero"}" ${ui.goAttr(risk_list({ risk_level: l, status: ["in", ui.OPEN_RISK] }))}><i style="background:${LEVEL[l]}"></i>${__(l)}<b>${cint(rk.by_level[l])}</b></span>`).join("")}</div>
				<div class="rk-matrix"><span class="rk-y">${__("Probability")} →</span><div class="ph3-heat">${ui.heatmap(rk.matrix, this.project)}</div><span class="rk-x">${__("Impact")} →</span></div>`
				: `<div class="ph2-empty">${__("No risks")}</div>`}</div>`;

		// ---- releases on a time line
		const rels = d.releases.filter((r) => r.due_date);
		let releases_html = `<div class="ph2-empty">${__("No releases")}</div>`;
		if (rels.length) {
			const dates = rels.map((r) => r.due_date).concat([today, info.expected_start_date, info.expected_end_date].filter(Boolean)).sort();
			const lo = dates[0];
			const span = Math.max(frappe.datetime.get_diff(dates[dates.length - 1], lo), 1);
			const pos = (date) => clamp((frappe.datetime.get_diff(date, lo) / span) * 100);
			const state = (r) => (flt(r.percent_complete) >= 100 ? "ok" : days_to(r.due_date) < 0 ? "bad" : days_to(r.due_date) <= 14 ? "warn" : "acc");
			// Labels that sit close together go to a free lane (two above the line, two below) so they never overlap.
			const lane_end = [-Infinity, -Infinity, -Infinity, -Infinity];
			const lane_of = {};
			[...rels].sort((a, b) => (a.due_date > b.due_date ? 1 : -1)).forEach((r) => {
				const x = pos(r.due_date);
				let lane = lane_end.findIndex((end) => x - end >= 9);
				if (lane < 0) lane = lane_end.indexOf(Math.min(...lane_end));
				lane_end[lane] = x;
				lane_of[r.name] = lane;
			});
			releases_html = `<div class="ph3-road">
				<div class="ph3-road-line"></div><em class="ph3-today" style="left:${pos(today)}%"><span>${__("Today")}</span></em>
				${rels.map((r) => `<a class="ph3-mile ph3-${state(r)} ph3-lane${lane_of[r.name]}" style="left:${pos(r.due_date)}%" href="/desk/release/${encodeURIComponent(r.name)}" title="${esc(r.release_name)} · ${flt(r.percent_complete, 0)}% · ${frappe.datetime.str_to_user(r.due_date)}">
					<i></i><span><b>${esc(r.release_name)}</b>${flt(r.percent_complete, 0)}%</span></a>`).join("")}
			</div>`;
		}
		const releases = `<div class="hub-panel ph2-card ph2-in"><div class="ph2-card-head"><h6>${__("Releases")}</h6>${ui.viewAll(ui.go("Release", { project: this.project }))}</div>${releases_html}</div>`;

		// ---- team as avatars grouped by role
		const by_role = {};
		d.members.forEach((m) => (by_role[m.project_role || "-"] = by_role[m.project_role || "-"] || []).push(m));
		const team = `<div class="hub-panel ph2-card ph2-in"><div class="ph2-card-head"><h6>${__("Team")}</h6><span class="ph2-sub">· ${d.members.length}</span>${ui.viewAll({ route: ["Form", "Project", this.project], filters: {} })}</div>
			${Object.entries(by_role).map(([role, list]) => `<div class="ph3-role"><span class="ph3-role-name">${esc(__(role))}</span><div class="ph3-faces">${list.map((m) => `<span class="ph2-avatar" title="${esc(m.full_name || m.user)}">${initials(m.full_name || m.user)}</span>`).join("")}</div></div>`).join("")}</div>`;

		this.$body.html(`<div class="ph2 ph3">
			${header}
			${gauges}
			${kpis}
			<div class="ph2-grid ph2-grid-3">${tickets}${workload}${risks}</div>
			${flow_card}
			${this.allocation_card(d)}
			<div class="ph2-grid ph3-grid-wide">${releases}${team}</div>
		</div>`);

		this.$body.find(".ph2-in").each((k, el) => (el.style.animationDelay = `${k * 40}ms`));
		const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
		this.$body.find("[data-count]").each((_k, el) => {
			const target = cint(el.getAttribute("data-count"));
			if (reduce || !target) return (el.textContent = el.textContent === "–" ? "–" : target);
			const start = performance.now();
			const step = (now) => {
				const t = Math.min(1, (now - start) / 700);
				el.textContent = Math.round(target * (1 - Math.pow(1 - t, 3)));
				if (t < 1) requestAnimationFrame(step);
			};
			requestAnimationFrame(step);
		});
		this.$body.find(".hub-tile[data-route]").on("click", (e) => this.open_tile($(e.currentTarget).data("route")));
		this.bind_risk_links();
		ui.bindTiles(this.$body);
	}

	bind_risk_links() {
		const project = this.project;
		this.$body.find("[data-risk-list]").on("click", (e) => {
			e.preventDefault();
			window.location.assign(`/desk/risk-register?project=${encodeURIComponent(project)}`);
		});
		this.$body.find("[data-risk-new]").on("click", (e) => {
			e.preventDefault();
			frappe.new_doc("Risk Register", { project });
		});
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



	// Weekly created / resolved / closed columns; each bar opens exactly its tickets, the rest of a week opens what was created
	flow_chart(fl, items) {
		const SERIES = [
			["created", __("Created"), "#6366f1", (k, end) => items({ creation: ["between", [fl.starts[k], end]] })],
			["resolved", __("Resolved"), "#06b6d4", (k) => items({ name: ["in", fl.resolved_names[k]] })],
			["closed", __("Closed"), "#10b981", (k, end) => items({ is_closed: 1, closed_on: ["between", [fl.starts[k], end]] })],
		];
		const weeks = fl.labels.length;
		const top = Math.max(1, ...SERIES.flatMap(([key]) => fl[key])) * 1.15;
		const W = 900, H = 180, left = 28, base = 150, bw = (W - left - 8) / weeks;
		const y = (v) => base - (v / top) * (base - 16);
		const step = Math.max(1, Math.ceil(top / 4 / 5) * 5);
		const grid = [];
		for (let v = 0; v <= top; v += step) grid.push(`<line x1="${left}" x2="${W - 4}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="fl-grid"/><text x="${left - 6}" y="${(y(v) + 3).toFixed(1)}" class="fl-ytext">${v}</text>`);
		const cols = fl.labels.map((label, k) => {
			const x0 = left + k * bw;
			const end = frappe.datetime.add_days(fl.starts[k], 6);
			const barw = Math.min(16, (bw * 0.7) / 3);
			const start = x0 + (bw - barw * 3 - 4) / 2;
			const bars = SERIES.map(([key, name, colour, target], j) => {
				const v = fl[key][k];
				const x = start + j * (barw + 2);
				return v ? `<g class="fl-bar" ${ui.goAttr(target(k, end))}><title>${name} · ${label}: ${v}</title>
					<rect x="${x.toFixed(1)}" y="${y(v).toFixed(1)}" width="${barw.toFixed(1)}" height="${(base - y(v)).toFixed(1)}" rx="3" style="fill:${colour};--d:${k * 40}ms"/>
					<text x="${(x + barw / 2).toFixed(1)}" y="${(y(v) - 4).toFixed(1)}" class="fl-v">${v}</text></g>` : "";
			}).join("");
			return `<g class="fl-week"><rect class="fl-hit" x="${x0.toFixed(1)}" y="8" width="${bw.toFixed(1)}" height="${base - 8}" ${ui.goAttr(SERIES[0][3](k, end))}><title>${label}</title></rect>${bars}
				${k % Math.ceil(weeks / 7) === 0 || k === weeks - 1 ? `<text x="${(x0 + bw / 2).toFixed(1)}" y="${H - 14}" class="fl-xtext">${label}</text>` : ""}</g>`;
		}).join("");
		return `<svg viewBox="0 0 ${W} ${H}" class="fl-svg">${grid.join("")}<line x1="${left}" x2="${W - 4}" y1="${base}" y2="${base}" class="fl-axis"/>${cols}</svg>
			<div class="fl-legend">${SERIES.map(([, name, colour]) => `<span><i style="background:${colour}"></i>${name}</span>`).join("")}<small>${__("Click a bar to open its tickets")}</small></div>`;
	}

	chart(selector, config, onPick) {
		ui.chart(this.$body, selector, config, onPick);
	}

	// Allocation & utilisation: hours planned per member (Allocation % of the weekly capacity) against the hours they logged
	allocation_card(d) {
		const a = d.allocation;
		const esc = frappe.utils.escape_html;
		const time = (filters) => ui.go("Time Entry", { project: this.project, ...filters });
		const STATE = {
			over: { label: __("Over-used"), chip: "ph2-chip-bad", colour: "#ef4444" },
			ok: { label: __("On plan"), chip: "ph2-chip-ok", colour: "#10b981" },
			under: { label: __("Under-used"), chip: "ph2-chip-warn", colour: "#f59e0b" },
			none: { label: __("Not allocated"), chip: "", colour: "#94a3b8" },
		};
		const h = (v) => `${flt(v, 1)}`;
		const has_alloc = a.members.some((m) => m.allocation_pct);

		// gauge: 0-150% on a half circle, under / on plan / over zones drawn as a thin band behind the value
		const G = 150;
		const frac = (v) => Math.max(0, Math.min(v, G)) / G;
		const point = (f, r) => [100 - r * Math.cos(Math.PI * f), 100 - r * Math.sin(Math.PI * f)];
		const arc = (f0, f1, r) => {
			const [x0, y0] = point(f0, r);
			const [x1, y1] = point(f1, r);
			return `M${x0.toFixed(1)} ${y0.toFixed(1)} A${r} ${r} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`;
		};
		const pct = a.utilisation_pct;
		const st = STATE[a.state];
		const [tx0, ty0] = point(frac(100), 70);
		const [tx1, ty1] = point(frac(100), 92);
		const gauge = `<div class="al-gauge al-${a.state}">
			<svg viewBox="0 0 200 112">
				<path d="${arc(0, frac(a.under_pct), 91)}" class="al-zone" style="stroke:${STATE.under.colour}"/>
				<path d="${arc(frac(a.under_pct), frac(a.over_pct), 91)}" class="al-zone" style="stroke:${STATE.ok.colour}"/>
				<path d="${arc(frac(a.over_pct), 1, 91)}" class="al-zone" style="stroke:${STATE.over.colour}"/>
				<path d="${arc(0, 1, 78)}" class="al-track"/>
				${pct === null ? "" : `<path d="${arc(0, 1, 78)}" class="al-value" pathLength="100" style="stroke:${st.colour};--p:${frac(pct) * 100}"/>`}
				<line x1="${tx0.toFixed(1)}" y1="${ty0.toFixed(1)}" x2="${tx1.toFixed(1)}" y2="${ty1.toFixed(1)}" class="al-tick"/>
			</svg>
			<div class="al-gauge-num"><b>${pct === null ? "–" : `${pct}<small>%</small>`}</b><span>${__("team utilisation")}</span></div>
			${pct === null ? "" : `<span class="ph2-chip ${st.chip}">${st.label}</span>`}
		</div>`;

		// stats: allocated, logged, free capacity, team mix and budget
		const free = flt(a.allocated_week - a.logged_week, 1);
		const mix = ["over", "ok", "under", "none"].filter((s) => a.counts[s]);
		const stats = `<div class="al-stats">
			<div class="al-stat"><span>${__("Allocated")}</span><b>${h(a.allocated_week)}<small> ${__("h/wk")}</small></b></div>
			<div class="al-stat"><span>${__("Logged")}</span><b>${h(a.logged_week)}<small> ${__("h/wk")}</small></b></div>
			<div class="al-stat"><span>${free >= 0 ? __("Spare") : __("Over plan")}</span><b class="${free < 0 ? "ph2-bad" : ""}">${h(Math.abs(free))}<small> ${__("h/wk")}</small></b></div>
			<div class="al-stat al-mix"><span>${__("Team")}</span>
				<div class="al-mixbar">${mix.map((s) => `<i style="flex:${a.counts[s]};background:${STATE[s].colour}" title="${STATE[s].label}: ${a.counts[s]}"></i>`).join("")}</div>
				<div class="al-mixkeys">${mix.map((s) => `<em><i style="background:${STATE[s].colour}"></i>${a.counts[s]} ${STATE[s].label}</em>`).join("")}</div></div>
			${d.numbers.hours_budget ? `<div class="al-stat al-budget"><span>${__("Budget used")}</span><b>${Math.round((d.numbers.hours_total / d.numbers.hours_budget) * 100)}<small>%</small></b>
				<div class="al-line"><i style="--w:${Math.min(100, (d.numbers.hours_total / d.numbers.hours_budget) * 100)}%"></i></div><small>${flt(d.numbers.hours_total, 0)} / ${flt(d.numbers.hours_budget, 0)} h</small></div>` : ""}
		</div>`;

		const hint = has_alloc
			? ""
			: `<div class="al-hint">${__("No allocation set yet. Add Allocation % to each member on the project's Auri PMS tab to compare planned and logged hours.")}${d.capabilities.can_manage_members ? ` <a href="/desk/project/${encodeURIComponent(this.project)}">${__("Open project")} →</a>` : ""}</div>`;
		const former = a.former_logged_week
			? `<div class="al-former">${__("{0} h/wk logged by people no longer on the team (not counted above).", [h(a.former_logged_week)])}</div>`
			: "";
		return `<div class="hub-panel ph2-card ph2-in al">
			<div class="ph2-card-head"><h6>${__("Allocation & utilisation")}</h6><span class="ph2-sub">· ${__("last {0} weeks", [a.weeks])} · ${__("capacity {0} h/week", [flt(a.capacity, 0)])}</span>${ui.viewAll(time({}))}</div>
			${hint}
			<div class="al-top">${gauge}${stats}</div>
			${former}
		</div>`;
	}

	// The final table of Health: tickets and billable time for Overall and a few periods, plus a custom range, from one request.
	draw_periods() {
		const $panel = this.$body.find(".hx-periods");
		if (!$panel.length) return;
		const today = frappe.datetime.get_today();
		const pr = (this.periods = this.periods || { from: frappe.datetime.add_days(today, -29), to: today });
		const ranges = [
			{ key: "all", label: __("Overall") },
			{ key: "7", label: __("Last 7 days"), from_date: frappe.datetime.add_days(today, -6), to_date: today },
			{ key: "30", label: __("Last 30 days"), from_date: frappe.datetime.add_days(today, -29), to_date: today },
			{ key: "90", label: __("Last 90 days"), from_date: frappe.datetime.add_days(today, -89), to_date: today },
			{ key: "year", label: __("This year"), from_date: `${today.slice(0, 4)}-01-01`, to_date: today },
			{ key: "custom", label: __("Custom range"), from_date: pr.from, to_date: pr.to },
		];
		const $body = $panel.find(".pf-tkt-body");
		const load = () => frappe.xcall("auri_pms.auri_pms.api.get_project_periods", { project: this.project, ranges: ranges.map(({ key, from_date, to_date }) => ({ key, from_date, to_date })) }).then((rows) => {
			pr.rows = rows;
			paint();
		});
		const paint = () => {
			const by = Object.fromEntries((pr.rows || []).map((r) => [r.key, r]));
			const wi = (extra) => ui.go("Work Item", { project: this.project, ...extra });
			const te = (extra) => ui.go("Time Entry", { project: this.project, ...extra });
			const cell = (value, cls, target) => `<td><span class="pf-tkn ${cls} ${value ? "" : "zero"}" ${value && target ? ui.goAttr(target) : ""}>${value}</span></td>`;
			const hours = (v, target) => `<td class="pf-hrs">${v && target ? `<span ${ui.goAttr(target)}>${flt(v, 1)} <small>${__("h")}</small></span>` : `${flt(v, 1)} <small>${__("h")}</small>`}</td>`;
			const share = (b, a) => {
				const pct = a ? Math.round((b / a) * 100) : null;
				return `<td>${pct === null ? "<span class='pf-na'>–</span>" : `<span class="pf-mini"><b>${pct}%</b><i style="--w:${pct}%"></i></span>`}</td>`;
			};
			$body.html(`<table class="table table-sm pf-ttable"><thead><tr><th>${__("Period")}</th><th>${__("Created")}</th><th>${__("Closed")}</th><th>${__("In progress")}</th><th>${__("Waiting on client")}</th><th>${__("Billable time")}</th><th>${__("Actual spent")}</th><th>${__("Billable share")}</th></tr></thead><tbody>${ranges
				.map((r) => {
					const v = by[r.key];
					const between = (field) => (r.from_date ? { [field]: ["between", [r.from_date, r.to_date]] } : {});
					const label = r.key === "custom"
						? `<b>${r.label}</b><div class="pf-tkt-dates"><input type="date" class="form-control" value="${pr.from}" data-edge="from"><span>→</span><input type="date" class="form-control" value="${pr.to}" data-edge="to"></div>`
						: `<b>${r.label}</b>`;
					if (!v) return `<tr><td>${label}</td><td colspan="7" class="text-muted small">${__("Loading...")}</td></tr>`;
					return `<tr><td>${label}</td>${cell(v.created, "pf-tk-created", wi(between("creation")))}${cell(v.closed, "pf-tk-closed", wi({ is_closed: 1, ...between("closed_on") }))}${cell(v.in_progress, "pf-tk-prog", wi({ is_closed: 0, status: "In Progress", ...between("creation") }))}${cell(v.client_dependent, "pf-tk-client", wi({ is_closed: 0, dependent_on_client: 1, ...between("creation") }))}${hours(v.billable_hours, te({ is_billable: 1, ...between("date") }))}${hours(v.spent_hours, te(between("date")))}${share(v.billable_hours, v.spent_hours)}</tr>`;
				})
				.join("")}</tbody></table>`);
			ui.bindTiles($body);
			$body.find(".pf-tkt-dates input").on("change", (e) => {
				const edge = $(e.currentTarget).data("edge");
				pr[edge] = $(e.currentTarget).val() || pr[edge];
				ranges.find((r) => r.key === "custom")[`${edge}_date`] = pr[edge];
				load();
			});
		};
		paint();
		load();
	}

	render_health(d, h) {
		const esc = frappe.utils.escape_html;
		const info = d.project;
		const f = h.flow;
		const t = h.time;
		const st = h.status;
		const per = h.bucket === "month" ? __("monthly") : __("weekly");
		const { bar, stack, panel, table, link } = ui;
		const split = (rows, field) =>
			stack(rows.map((r) => [__(r.label), r.count - r.client, r.client]), [__("With us"), __("Waiting on client")], ["seg-blue", "seg-orange"], rows.map((r) => ui.go("Work Item", { project: this.project, is_closed: 0, [field]: r.label })));
		const waiting_panel = panel(
			`${__("Waiting on client")} (${f.client_dependent})${ui.viewAll(ui.goReport("Client Dependencies", { project: this.project }))}`,
			d.client_tickets.length
				? d.client_tickets.map((t) => `<a class="ph2-row" href="/desk/work-item/${encodeURIComponent(t.name)}"><span class="ph2-id">${esc(t.name)}</span>
					<span class="ph2-grow">${esc(t.subject)}${t.note ? `<small>${__("What we need")}: ${esc(t.note)}</small>` : ""}</span>
					<span class="ph2-chip ${t.days > 7 ? "ph2-chip-bad" : "ph2-chip-warn"}">${ui.days(t.days)}</span></a>`).join("")
				: `<div class="text-muted small">${__("Nothing is waiting on the client.")}</div>`
		);
		const has_modules = f.by_module.some((r) => r.label !== __("(no module)"));
		const module_panel = has_modules
			? panel(__("Open vs closed (by module)") + ui.viewAll(ui.go("Work Item", { project: this.project })), stack(f.by_module.map((r) => [r.label, r.open, r.client, r.closed]), [__("Open (with us)"), __("Waiting on client"), __("Closed")], ["seg-blue", "seg-orange", "seg-green"], f.by_module.map((r) => ui.go("Work Item", { project: this.project, ...(r.label === __("(no module)") ? {} : { project_module: r.label }) }))))
			: "";
		const rk = h.risks;
		const risk_health = panel(
			`${__("Risk register")} (${rk.open} ${__("open")})<span style="float:right" class="small"><a href="#" data-risk-list>${__("View all")} →</a>${d.capabilities.can_create_items ? ` &middot; <a href="#" data-risk-new>${__("New risk")}</a>` : ""}</span>`,
			rk.total
				? `${ui.riskLevelCounts(rk.by_level, this.project)}${rk.overdue ? `<div class="hub-sub" style="margin-bottom:8px">${__("{0} past the mitigation date", [rk.overdue])}</div>` : ""}<div class="hub-risk-split"><div>${ui.heatmap(rk.matrix, this.project)}</div><div>${ui.riskTable(rk.top.slice(0, 5).map((r) => ({ ...r, project_label: "" })))}</div></div>`
				: `<div class="text-muted small">${__("No risks have been registered for this project.")}</div>`
		);
		const items = (filters) => ui.go("Work Item", { project: this.project, ...filters });
		const entries = (filters) => ui.go("Time Entry", { project: this.project, ...filters });
		const tile = (value, label, cls, sub, route) => ui.tile(value, label, cls, sub, route);
		const gauge = (value, label, sub, tone, target) => `<div class="hub-panel ph3-gauge ph2-in" ${target ? ui.goAttr(target) : ""}>
			<div class="ph2-ring ph3-ring ${tone}" style="--p:${value === null || value === undefined ? 0 : Math.min(100, value)}">
				<svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="ph2-ring-bg"/><circle cx="60" cy="60" r="52" class="ph2-ring-fg" pathLength="100"/></svg>
				<div><div class="ph2-ring-num"><b>${value === null || value === undefined ? "–" : flt(value, 0)}</b>${value === null || value === undefined ? "" : "<span>%</span>"}</div></div>
			</div><strong>${label}</strong><small>${sub || ""}</small></div>`;
		const risk_badge = (r) => `<span class="hub-badge hub-risk-${r.risk}">${r.risk === "late" ? __("Late") : r.risk === "risk" ? __("At Risk") : __("On Track")}</span>`;
		const releases = h.releases.length
			? h.releases
					.map(
						(r) => `<div class="ph2-rel" ${ui.goAttr({ route: ["Form", "Release", r.name], filters: {} })}>
							<div><b>${esc(r.label)}</b>${risk_badge(r)}</div>
							<div class="ph2-bar ph2-bar-sm"><i style="--w:${flt(r.percent)}%"></i></div>
							<div class="ph2-sub">${flt(r.percent, 0)}% · ${__("due")} ${r.due_date ? frappe.datetime.str_to_user(r.due_date) : "-"}${r.days_left === null ? "" : ` · ${r.days_left < 0 ? __("{0} days overdue", [-r.days_left]) : __("{0} days left", [r.days_left])}`}</div></div>`
					)
					.join("")
			: `<div class="text-muted small">${__("No open releases")}</div>`;
		const hours_max = Math.max(t.budget || 0, t.estimated, t.spent, 1);
		const pct = (n) => (f.total ? (n / f.total) * 100 : 0);
		const with_us = f.open - f.client_dependent;
		const open_closed = `<div class="hub-meter"><i class="seg-blue" style="width:${pct(with_us)}%">${with_us}</i><i class="seg-orange" style="width:${pct(f.client_dependent)}%">${f.client_dependent || ""}</i><i class="seg-green" style="width:${pct(f.closed)}%">${f.closed}</i></div>` +
			stack(f.by_tracker.map((r) => [__(r.label), r.open, r.client, r.closed]), [__("Open (with us)"), __("Waiting on client"), __("Closed")], ["seg-blue", "seg-orange", "seg-green"], f.by_tracker.map((r) => ui.go("Work Item", { project: this.project, tracker: r.label })));
		const people_open = panel(__("Open tickets by person") + ui.viewAll(ui.go("Work Item", { project: this.project, is_closed: 0 })), h.workload.length ? h.workload.map((w) => bar(w.name, w.open, Math.max(...h.workload.map((x) => x.open)))).join("") : `<div class="text-muted small">${__("Nothing open")}</div>`);
		const people_hours = panel(__("Hours by person (billable vs non-billable)") + ui.viewAll(ui.go("Time Entry", { project: this.project })), stack(t.by_user.map((u) => [u.name, u.billable, u.non_billable]), [__("Billable"), __("Non-billable")], ["seg-green", "seg-orange"]));

		const p_flow = panel(`${__("Tickets created vs resolved")} (${per})${ui.viewAll(ui.go("Work Item", { project: this.project }))}`, `<div class="hub-chart" id="hc-flow"></div><div class="small text-muted mt-2">${__("{0} created · {1} resolved", [f.created_total, f.resolved_total]) + (f.created_waiting ? ` · ${__("{0} waiting on client", [f.created_waiting])}` : "")}</div>`);
		const p_trend = panel(`${__("Open backlog trend")} (${per})${ui.viewAll(ui.go("Work Item", { project: this.project, is_closed: 0 }))}`, `<div class="hub-chart" id="hc-trend"></div>`);
		const p_type = panel(__("Open vs closed (by type)") + ui.viewAll(ui.go("Work Item", { project: this.project })), open_closed);
		const status_total = f.open_by_status.reduce((a, r) => a + r.count, 0);
		const status_shades = ["#5b21b6", "#7c3aed", "#8b5cf6", "#a78bfa", "#c4b5fd", "#ddd6fe"];
		let status_offset = 0;
		const status_arcs = f.open_by_status.map((r, k) => {
			const share = status_total ? (r.count / status_total) * 100 : 0;
			const arc = `<circle cx="60" cy="60" r="44" pathLength="100" stroke="${status_shades[k % status_shades.length]}" stroke-dasharray="${share} ${100 - share}" stroke-dashoffset="${-status_offset}" ${ui.goAttr(items({ is_closed: 0, status: r.label }))}><title>${esc(__(r.label))}: ${r.count}</title></circle>`;
			status_offset += share;
			return arc;
		});
		const p_status = panel(
			__("Open by status (with us vs waiting on client)") + ui.viewAll(ui.go("Work Item", { project: this.project, is_closed: 0 })),
			status_total
				? `<div class="ph3-donut-wrap"><div class="ph3-donut"><svg viewBox="0 0 120 120">${status_arcs.join("")}</svg><div><b>${status_total}</b><small>${__("open")}</small></div></div>
					<div class="ph3-keys ph3-keys-3">${f.open_by_status.map((r, k) => `<span ${ui.goAttr(items({ is_closed: 0, status: r.label }))}><i style="background:${status_shades[k % status_shades.length]}"></i>${esc(__(r.label))}<b>${r.count}</b><em>${__("{0} with us · {1} waiting", [r.count - r.client, r.client])}</em></span>`).join("")}</div></div>`
				: `<div class="text-muted small">${__("Nothing open")}</div>`
		);
		const p_prio = panel(__("Open tickets by priority") + ui.viewAll(ui.go("Work Item", { project: this.project, is_closed: 0 })), split(f.open_by_priority, "priority"));
		// billing panels are shared with the Portfolio; here they describe this one project
		const { bill, cats } = ui.mergeBilling([h.billing]);
		const p_bill = ui.billingPanel(this.project);
		const p_tk = ui.billableTicketsPanel(bill, this.project);
		const category = ui.categoryPanel(cats, this.project);
		const p_cat = category.html;
		const billable_share = t.spent ? Math.round((t.billable * 100) / t.spent) : null;
		const p_est = panel(__("Estimated vs spent vs billable hours") + ui.viewAll(ui.go("Time Entry", { project: this.project })), `${t.budget ? bar(__("Budget"), t.budget, hours_max) : ""}${bar(__("Estimated"), t.estimated, hours_max)}${bar(__("Spent"), t.spent, hours_max)}${bar(__("Billable"), t.billable, hours_max)}${bar(__("Non-billable"), t.non_billable, hours_max)}<div class="small text-muted mt-2">${billable_share === null ? __("No hours logged yet") : __("Billable is {0}% of the {1} h spent", [billable_share, flt(t.spent, 1)])}</div>`);
		const p_activity = panel(__("Hours by activity (billable vs non-billable)") + ui.viewAll(ui.go("Time Entry", { project: this.project })), stack(t.by_activity.map((a) => [a.label, a.billable, a.non_billable]), [__("Billable"), __("Non-billable")], ["seg-green", "seg-orange"]));
		const p_vel = panel(__("Sprint velocity (tickets closed per completed sprint)") + ui.viewAll(ui.go("Sprint", { project: this.project })), h.velocity.length ? `<div class="hub-chart" id="hc-velocity"></div><div class="small text-muted mt-2">${__("Average {0} tickets / {1} hours per sprint", [flt(h.velocity.reduce((a, v) => a + v.items, 0) / h.velocity.length, 1), flt(h.velocity.reduce((a, v) => a + v.hours, 0) / h.velocity.length, 1)])}</div>` : `<div class="text-muted small">${__("No completed sprints yet")}</div>`);
		const age_day = (n) => frappe.datetime.add_days(frappe.datetime.get_today(), -n);
		const age_ranges = [["between", [age_day(7), frappe.datetime.get_today()]], ["between", [age_day(14), age_day(8)]], ["between", [age_day(30), age_day(15)]], ["between", [age_day(60), age_day(31)]], ["<", age_day(60)]];
		// team load: allocation across projects against 100% of the week, and who is over-allocated or at burnout risk
		const tm = h.team;
		const tm_state = { over: ["ph2-chip-bad", __("Over-used")], under: ["ph2-chip-warn", __("Under-used")], ok: ["ph2-chip-ok", __("On plan")], none: ["", __("Not allocated")] };
		const tm_since = frappe.datetime.add_days(frappe.datetime.get_today(), -7 * tm.weeks + 1);
		const p_team = panel(
			`${__("Team load and burnout risk")}<span class="pf-cap-note" style="margin-left:10px">${__("last {0} weeks · {1} h week", [tm.weeks, flt(tm.capacity, 0)])}</span>`,
			tm.people.length
				? `<div class="pf-cap-sum"><div><span>${__("People")}</span><b>${tm.people.length}</b></div><div><span>${__("Over-allocated")}</span><b class="${tm.over_allocated ? "ph2-bad" : ""}">${tm.over_allocated}</b></div><div><span>${__("Burnout risk")}</span><b class="${tm.burnout ? "ph2-bad" : ""}">${tm.burnout}</b></div></div>`
					+ tm.people.map((m) => `<div class="al-cap-row pf-cap-row" ${ui.goAttr(ui.go("Time Entry", { user: m.user, date: [">=", tm_since] }))}>
						<span class="al-cap-name" title="${esc(m.name)}">${esc(m.name)}</span>
						<div class="al-cap-bar ${m.over_allocated ? "al-cap-over" : ""}"><i style="width:${Math.min(100, (m.total_pct / Math.max(120, m.total_pct)) * 100)}%;background:#7c3aed"></i></div>
						<b class="${m.over_allocated ? "ph2-bad" : ""}">${m.total_pct}%</b>
						<small>${__("{0} of {1} h/wk", [flt(m.logged_week, 1), flt(m.allocated_week, 1)])}</small>
						<span>${m.over_allocated ? `<span class="ph2-chip ph2-chip-bad">${__("Over-allocated")}</span>` : ""}${m.burnout ? `<span class="ph2-chip ph2-chip-bad">${__("Burnout risk")}</span>` : ""}${!m.over_allocated && !m.burnout ? `<span class="ph2-chip ${tm_state[m.state][0]}">${m.utilisation_pct === null ? "" : `${m.utilisation_pct}% · `}${tm_state[m.state][1]}</span>` : ""}</span></div>`).join("")
				: `<div class="text-muted small">${__("This project has no members yet.")}</div>`
		);
		const p_age = panel(
			__("Age of open tickets") + ui.viewAll(ui.go("Work Item", { project: this.project, is_closed: 0 })),
			stack(f.aging.map((a) => [a.label, a.count - a.client, a.client]), [__("With us"), __("Waiting on client")], ["seg-blue", "seg-orange"], f.aging.map((_a, i) => ui.go("Work Item", { project: this.project, is_closed: 0, creation: age_ranges[i] })))
		);
		const p_rel = panel(__("Releases") + ui.viewAll(ui.go("Release", { project: this.project })), `<div class="ph3-rel-scroll">${releases}</div>`);
		// two panels per row, so panels side by side share one height; a lone panel takes the full row
		const row = (...cells) => {
			const items = cells.filter(Boolean);
			return items.length ? `<div class="hub-row hub-row-even ${items.length === 1 ? "hub-row-one" : ""}">${items.join("")}</div>` : "";
		};

		const row3 = (...cells) => `<div class="hub-row hub-row-3">${cells.filter(Boolean).join("")}</div>`;
		const section = (no, title, html) => (html.trim() ? `<section class="hx-section"><div class="hx-section-head"><span>${no}</span><h3>${title}</h3></div>${html}</section>` : "");

		// ---- hero: report title, health score gauge, the four key figures, the reasons and how the score is worked out
		const level_label = st ? st.label : __("Health not shown");
		const score = st && st.score !== null && st.score !== undefined ? st.score : null;
		const level = st ? st.level : "none";
		const left = info.expected_end_date ? frappe.datetime.get_diff(info.expected_end_date, frappe.datetime.get_today()) : null;
		const metric = (value, label, sub, target, tone) => `<div class="hx-metric ${tone || ""}" ${target ? ui.goAttr(target) : ""}>
			<span>${label}</span><b>${value === null || value === undefined ? "–" : `${flt(value, 0)}<small>%</small>`}</b>
			<div class="hx-meter"><i style="--w:${value === null || value === undefined ? 0 : Math.min(100, value)}%"></i></div><em>${sub || ""}</em></div>`;
		const reasons = st && st.reasons && st.reasons.length
			? `<div class="hx-reasons">${st.reasons
					.map((r) => `<div class="hx-reason hx-${r.level}" ${r.link ? ui.goAttr(r.link) : ""}><i></i><span>${esc(r.text)}</span>${st.calc && (r.level === "red" || r.level === "amber") ? `<b>−${r.level === "red" ? st.calc.red_penalty : st.calc.amber_penalty}</b>` : ""}</div>`)
					.join("")}</div>`
			: "";
		// closed by default: one button; the score formula, the reasons with their points and the explanation open from it
		const fold = reasons || (st && st.calc)
			? `<details class="hx-why"><summary><span class="hx-why-btn">ⓘ ${__("How is it worked out?")}</span></summary>
				<div class="hx-why-body">${st && st.calc ? `<div class="hx-why-score"><b>${__("Score")}</b><span class="hx-formula">${esc(ui.scoreCalc(st.calc, st.score))}</span></div>` : ""}${reasons}${st && st.calc ? `<div class="hx-working"><small>${esc(__("The score starts at 100. Each Off Track (red) reason takes off {0} points (PMS Settings: Health Score Penalty per Off Track Reason) and each At Risk (amber) reason takes off {1} (Health Score Penalty per At Risk Reason).", [st.calc.red_penalty, st.calc.amber_penalty])).replace("PMS Settings", `<a href="/desk/pms-settings">PMS Settings</a>`)}</small></div>` : ""}</div></details>`
			: "";
		const hero = `<div class="hub-panel hx-hero hx-${level}${st ? "" : " hx-nostatus"}">
			<div class="hx-hero-top">
				<div><div class="hx-eyebrow">${__("Project health report")}</div><h1>${esc(info.project_name || info.name)}</h1>
					<div class="hx-meta"><span class="hx-ident">${esc(info.tracker_identifier)}</span>${__(ui.PERIOD_NOTE[h.period])} · ${frappe.datetime.str_to_user(frappe.datetime.get_today())}</div>
						${h.can_note ? `<div class="hx-notes pf-card-foot">${ui.noteFoot({ name: this.project, notes: h.notes })}</div>` : ""}</div>
				${info.expected_start_date || info.expected_end_date ? `<div class="hx-dates"><span>${info.expected_start_date ? frappe.datetime.str_to_user(info.expected_start_date) : "–"} → ${info.expected_end_date ? frappe.datetime.str_to_user(info.expected_end_date) : "–"}</span>
					${left === null ? "" : `<b>${left < 0 ? __("{0} days overdue", [-left]) : __("{0} days left", [left])}</b>`}</div>` : ""}
			</div>
			<div class="hx-hero-body">
				${st ? `				<div class="hx-score">
					<svg viewBox="0 0 200 116"><path d="M20 100 A80 80 0 0 1 180 100" class="hx-arc-bg"/><path d="M20 100 A80 80 0 0 1 180 100" class="hx-arc" pathLength="100" style="stroke-dasharray:${score === null ? 0 : score} 100"/></svg>
					<div><b>${score === null ? "–" : score}</b><span>${__("health score")}</span></div>
					<em class="hx-level">${esc(level_label)}</em>
				</div>` : ""}
				<div class="hx-metrics">
					${metric(f.completion_pct, __("Complete"), __("{0} of {1} tickets", [f.closed, f.total]), items())}
					${metric(f.overdue_pct, __("Open & overdue"), __("{0} tickets", [f.overdue]), items({ is_closed: 0, due_date: ["<", frappe.datetime.get_today()] }), f.overdue ? "hx-metric-bad" : "")}
					${metric(t.burn_pct, __("Hours spent"), `${flt(t.spent, 1)} h${t.burn_pct === null ? "" : ` · ${t.budget ? __("{0}% of budget", [t.burn_pct]) : __("{0}% of estimate", [t.burn_pct])}`}`, entries(), t.burn_pct !== null && t.burn_pct > 100 ? "hx-metric-bad" : "")}
					${metric(t.billable_pct, __("Billable hours"), `${flt(t.billable, 1)} h · ${__("{0}% of spent", [t.billable_pct])}`, entries({ is_billable: 1 }))}
				</div>
			</div>
			${fold ? `<div class="hx-hero-foot hx-foot-fold">${fold}</div>` : ""}
		</div>`;

		const panes = [
			["overview", __("Overview"), `<div class="hub-tiles hx-tiles">
				${tile(f.open, __("Open tickets"), "hub-blue", `${f.client_dependent ? `${__("{0} waiting on client", [f.client_dependent])} · ` : ""}${__("{0} h estimated", [f.estimated_open_hours])}`, items({ is_closed: 0 }))}
				${tile(f.closed, __("Closed tickets"), "hub-green", __("{0} h estimated", [f.estimated_closed_hours]), items({ is_closed: 1 }))}
				${tile(f.client_dependent, __("Waiting on client"), f.client_dependent ? "hub-orange" : "hub-teal", f.client_oldest_days === null ? "" : __("oldest {0} days", [f.client_oldest_days]), ui.goReport("Client Dependencies", { project: this.project }))}
				${tile(t.non_billable, __("Non-billable hours"), "hub-orange", "", entries({ is_billable: 0 }))}
			</div>${section("01", __("Delivery"), row(p_flow, p_trend))}${section("02", __("Risk"), row(risk_health))}`],
			["work", __("Work"), section("01", __("Open work"), row3(p_status, p_prio, p_age)) + section("02", __("Breakdown"), row(p_type, module_panel)) + section("03", __("Client and effort"), row(waiting_panel, p_est))],
			["time", __("Time and billing"), section("01", __("Billing and time"), row(p_bill, p_tk) + row(p_cat, p_activity)) + section("02", __("Tickets and billable time by period"), `<div class="hub-panel pf-tkt hx-periods"><div class="pf-tkt-body"></div>
				<div class="pf-note pf-tkt-note">${__("Created and Closed count the tickets created and closed in the period; In progress and Waiting on client count the open tickets created in the period that are in progress or waiting on the client now. Billable time and hours count the time logged in the period.")}</div></div>`)],
			["people", __("People"), section("01", __("People"), row(p_team) + row(people_hours, people_open))],
			["plan", __("Plan"), section("01", __("Plan"), row(p_vel, p_rel))],
		];
		this.pane = panes.some((x) => x[0] === this.pane) ? this.pane : "overview";
		this.$body.html(`<div class="hx">
			${hero}
			<nav class="hx-panes">${panes.map(([key, label]) => `<button type="button" class="hx-pane-btn ${key === this.pane ? "on" : ""}" data-pane="${key}">${label}</button>`).join("")}</nav>
			${panes.map(([key, , html]) => `<div class="hx-pane ${key === this.pane ? "on" : ""}" data-pane="${key}">${html}</div>`).join("")}`);
		this.$body.find(".hx-pane-btn").on("click", (e) => {
			this.pane = $(e.currentTarget).data("pane");
			this.$body.find(".hx-pane-btn, .hx-pane").each((_i, el) => $(el).toggleClass("on", $(el).data("pane") === this.pane));
			window.dispatchEvent(new Event("resize")); // charts that were hidden draw at their real width
		});

		this.bind_risk_links();
		ui.bindTiles(this.$body);
		this.$body.find("[data-open-report]").on("click", (e) => {
			e.preventDefault();
			this.open_tile("client");
		});
		const weeks = h.labels;
		const palette = { blue: "#7c3aed", green: "#c4b5fd", orange: "#fb923c", purple: "#8b5cf6", cyan: "#a78bfa", red: "#e11d48", pink: "#db2777" };
		this.chart("#hc-flow", { type: "bar", height: 220, data: { labels: weeks, datasets: [{ name: __("Created"), values: f.created }, { name: __("Resolved"), values: f.resolved }] }, colors: [palette.blue, palette.green], barOptions: { spaceRatio: 0.4 }, axisOptions: { xIsSeries: 1, xAxisMode: "tick" }});
		this.chart("#hc-trend", { type: "line", height: 220, data: { labels: weeks, datasets: [{ name: __("Open tickets"), values: f.open_trend }, { name: __("Waiting on client"), values: f.client_trend }] }, colors: [palette.purple, palette.orange], lineOptions: { regionFill: 1 }, axisOptions: { xIsSeries: 1, xAxisMode: "tick" }});
		ui.drawBilling(this.$body, { labels: weeks, starts: h.starts, billable: t.billable_by_week, non_billable: t.non_billable_by_week, project: this.project });
		category.bind(this.$body);
		if (h.can_note) {
			ui.bindNotes(this.$body, () => ui.openNotes(this.project, info.project_name || info.name, (notes) => {
				h.notes = { count: notes.length, last: notes[0] ? { text: notes[0].text, by_name: notes[0].by_name || notes[0].by, on: notes[0].on } : null };
				this.$body.find(".hx-notes").html(ui.noteFoot({ name: this.project, notes: h.notes }));
				ui.bindNotes(this.$body, () => this.$body.find(".pf-note-btn").first().trigger("click"));
			}));
		}
		this.draw_periods();
		if (h.velocity.length) this.chart("#hc-velocity", { type: "bar", height: 220, data: { labels: h.velocity.map((v) => v.sprint), datasets: [{ name: __("Tickets closed"), values: h.velocity.map((v) => v.items) }] }, colors: [palette.purple], barOptions: { spaceRatio: 0.5 } }, (i) => ui.openTarget(ui.go("Work Item", { project: this.project, sprint: h.velocity[i].name, is_closed: 1 })));
		this.chart("#hc-aging", { type: "bar", height: 220, data: { labels: f.aging.map((a) => a.label), datasets: [{ name: __("With us"), values: f.aging.map((a) => a.count - a.client) }, { name: __("Waiting on client"), values: f.aging.map((a) => a.client) }] }, colors: [palette.blue, palette.orange], barOptions: { stacked: 1, spaceRatio: 0.5 } }, (i) => {
			const day = (n) => frappe.datetime.add_days(frappe.datetime.get_today(), -n);
			const ranges = [["between", [day(7), frappe.datetime.get_today()]], ["between", [day(14), day(8)]], ["between", [day(30), day(15)]], ["between", [day(60), day(31)]], ["<", day(60)]];
			ui.openTarget(ui.go("Work Item", { project: this.project, is_closed: 0, creation: ranges[i] }));
		});
	}




}
