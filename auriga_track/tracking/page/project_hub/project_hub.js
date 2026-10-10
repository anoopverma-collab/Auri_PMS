// Copyright (c) 2026, Auriga IT and contributors
// For license information, please see license.txt

// Project Hub: pick a project, then work inside it (tickets, board, sprints, releases, team, time, reports).
const HUB_API = "auriga_track.tracking.api";

frappe.pages["project-hub"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Project Hub"), single_column: true });
	wrapper.project_hub = new ProjectHub(page, wrapper);
};

frappe.pages["project-hub"].on_page_show = function (wrapper) {
	const route = frappe.get_route();
	wrapper.project_hub.show(route[1], route[2]);
};

// Hub themes. Every theme has a light and a dark palette and follows Frappe's own light/dark switch.
// Tokens: bg, b1/b3 (backdrop glows), glass, strong (raised surface), border, text, muted, nl/nd (soft-UI light/dark
// shadow colours), acc (accent), bar (progress gradient), blur (px), d (shadow offset px), bm (shadow blur multiplier),
// r (radius px) and optional p (four pastel panel colours used by the bento themes).
const NONE = "rgba(0,0,0,0)";
const HUB_THEMES = {
	glass: {
		label: "Glass + Soft",
		light: { bg: "linear-gradient(135deg,#dfe7ff 0%,#ece4ff 45%,#d3f3f7 100%)", b1: "rgba(99,102,241,.30)", b3: "rgba(20,184,166,.24)", glass: "rgba(255,255,255,.45)", strong: "rgba(255,255,255,.72)", border: "rgba(255,255,255,.8)", text: "#1f2937", muted: "#6b7280", nl: "rgba(255,255,255,.95)", nd: "rgba(148,163,184,.40)", acc: "#6366f1", bar: "linear-gradient(90deg,#6366f1,#ec4899)", blur: 18, d: 7, bm: 2.2, r: 22 },
		dark: { bg: "linear-gradient(135deg,#151826 0%,#1b1633 50%,#10242b 100%)", b1: "rgba(99,102,241,.32)", b3: "rgba(20,184,166,.22)", glass: "rgba(34,39,56,.55)", strong: "rgba(42,48,70,.78)", border: "rgba(255,255,255,.09)", text: "#e5e7eb", muted: "#9ca3af", nl: "rgba(255,255,255,.045)", nd: "rgba(0,0,0,.55)", acc: "#818cf8", bar: "linear-gradient(90deg,#6366f1,#ec4899)", blur: 18, d: 7, bm: 2.2, r: 22 },
	},
	soft: {
		label: "Soft UI (Neumorphism)",
		light: { bg: "#e4e8ef", b1: "transparent", b3: "transparent", glass: "#e4e8ef", strong: "#e9edf3", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(163,177,198,.75)", acc: "#4f46e5", bar: "linear-gradient(90deg,#4f46e5,#7c3aed)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#25282e", b1: "transparent", b3: "transparent", glass: "#25282e", strong: "#2b2f36", border: "transparent", text: "#e5e7eb", muted: "#9ca3af", nl: "rgba(255,255,255,.06)", nd: "rgba(0,0,0,.6)", acc: "#818cf8", bar: "linear-gradient(90deg,#6366f1,#a78bfa)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	minimal: {
		label: "Minimal Clean",
		light: { bg: "#f7f7f8", b1: "transparent", b3: "transparent", glass: "#ffffff", strong: "#ffffff", border: "#e5e7eb", text: "#111827", muted: "#6b7280", nl: "rgba(255,255,255,0)", nd: "rgba(17,24,39,.10)", acc: "#2563eb", bar: "linear-gradient(90deg,#2563eb,#2563eb)", blur: 0, d: 1, bm: 3, r: 12 },
		dark: { bg: "#0b0b0c", b1: "transparent", b3: "transparent", glass: "#151517", strong: "#1b1b1e", border: "#2a2a2e", text: "#f3f4f6", muted: "#9ca3af", nl: "rgba(255,255,255,0)", nd: "rgba(0,0,0,.6)", acc: "#60a5fa", bar: "linear-gradient(90deg,#60a5fa,#60a5fa)", blur: 0, d: 1, bm: 3, r: 12 },
	},
	"flat-solid": {
		label: "Flat - Solid colour",
		light: { bg: "#eef1f6", b1: "transparent", b3: "transparent", glass: "#ffffff", strong: "#ffffff", border: "#dfe4ec", text: "#1b2430", muted: "#5f6c7b", nl: NONE, nd: NONE, acc: "#2563eb", bar: "linear-gradient(90deg,#2563eb,#2563eb)", blur: 0, d: 0, bm: 0, r: 8 },
		dark: { bg: "#10151d", b1: "transparent", b3: "transparent", glass: "#19212c", strong: "#202a37", border: "#2a3544", text: "#e8edf3", muted: "#98a5b5", nl: NONE, nd: NONE, acc: "#4f8df7", bar: "linear-gradient(90deg,#4f8df7,#4f8df7)", blur: 0, d: 0, bm: 0, r: 8 },
	},
	"flat-tint": {
		label: "Flat - Tinted",
		light: { bg: "#f7f8fa", b1: "transparent", b3: "transparent", glass: "#ffffff", strong: "#ffffff", border: "#e8eaee", text: "#202328", muted: "#6b7280", nl: NONE, nd: NONE, acc: "#7c3aed", bar: "linear-gradient(90deg,#7c3aed,#7c3aed)", blur: 0, d: 0, bm: 0, r: 12 },
		dark: { bg: "#0f1012", b1: "transparent", b3: "transparent", glass: "#17181b", strong: "#1d1e22", border: "#26282c", text: "#ececf0", muted: "#9a9ca5", nl: NONE, nd: NONE, acc: "#a78bfa", bar: "linear-gradient(90deg,#a78bfa,#a78bfa)", blur: 0, d: 0, bm: 0, r: 12 },
	},
	"flat-line": {
		label: "Flat - Outline",
		light: { bg: "#ffffff", b1: "transparent", b3: "transparent", glass: "#ffffff", strong: "#f8fafc", border: "#d4d8df", text: "#111418", muted: "#667085", nl: NONE, nd: NONE, acc: "#0f766e", bar: "linear-gradient(90deg,#0f766e,#0f766e)", blur: 0, d: 0, bm: 0, r: 4 },
		dark: { bg: "#0a0d10", b1: "transparent", b3: "transparent", glass: "#0e1216", strong: "#131920", border: "#2a323b", text: "#f1f5f9", muted: "#94a3b8", nl: NONE, nd: NONE, acc: "#2dd4bf", bar: "linear-gradient(90deg,#2dd4bf,#2dd4bf)", blur: 0, d: 0, bm: 0, r: 4 },
	},
	"bento-pastel": {
		label: "Bento - Pastel",
		light: { bg: "#f1efe9", b1: "transparent", b3: "transparent", glass: "#ffffff", strong: "#ffffff", border: "transparent", text: "#1d1d1f", muted: "#6e6e73", nl: NONE, nd: NONE, acc: "#1d1d1f", bar: "linear-gradient(90deg,#1d1d1f,#6e6e73)", blur: 0, d: 0, bm: 0, r: 28, p: ["#dfe9ff", "#fbe4ec", "#e4f5df", "#fff1cf"] },
		dark: { bg: "#0d0d0f", b1: "transparent", b3: "transparent", glass: "#1a1a1d", strong: "#232327", border: "transparent", text: "#f5f5f7", muted: "#9a9aa1", nl: NONE, nd: NONE, acc: "#f5f5f7", bar: "linear-gradient(90deg,#f5f5f7,#9a9aa1)", blur: 0, d: 0, bm: 0, r: 28, p: ["#1c2540", "#3a1f2b", "#1f3326", "#3b3220"] },
	},
	"bento-vivid": {
		label: "Bento - Vivid",
		light: { bg: "#e9ecf2", b1: "transparent", b3: "transparent", glass: "#ffffff", strong: "#ffffff", border: "transparent", text: "#11141a", muted: "#5d6675", nl: NONE, nd: NONE, acc: "#4f46e5", bar: "linear-gradient(90deg,#4f46e5,#ec4899)", blur: 0, d: 0, bm: 0, r: 26 },
		dark: { bg: "#08090c", b1: "transparent", b3: "transparent", glass: "#14161b", strong: "#1b1e24", border: "transparent", text: "#f4f5f8", muted: "#98a0ae", nl: NONE, nd: NONE, acc: "#818cf8", bar: "linear-gradient(90deg,#818cf8,#f472b6)", blur: 0, d: 0, bm: 0, r: 26 },
	},
};
const HUB_THEME_KEY = "auriga_hub_theme";
const HUB_PERIODS = { "1m": "1 month", "3m": "3 months", "6m": "6 months", all: "Overall" };
const HUB_PERIOD_NOTE = { "1m": "last month", "3m": "last 3 months", "6m": "last 6 months", all: "overall" };

function hub_theme_css() {
	const vars = (t) =>
		`--g-bg:${t.bg};--g-blob1:${t.b1};--g-blob3:${t.b3};--g-glass:${t.glass};--g-glass-strong:${t.strong};--g-border:${t.border};` +
		`--g-text:${t.text};--g-muted:${t.muted};--n-light:${t.nl};--n-dark:${t.nd};--acc:${t.acc};--bar:${t.bar};` +
		`--blur:${t.blur}px;--d:${t.d}px;--bm:${t.bm};--radius:${t.r}px;` +
		(t.p ? t.p.map((c, i) => `--p${i + 1}:${c};`).join("") : "");
	return Object.entries(HUB_THEMES)
		.map(
			([key, t]) =>
				`.auriga-hub[data-hub-theme="${key}"]{${vars(t.light)}}` +
				`html[data-theme="dark"] .auriga-hub[data-hub-theme="${key}"]{${vars(t.dark)}}`
		)
		.join("\n");
}

class ProjectHub {
	constructor(page, wrapper) {
		this.page = page;
		this.$body = $(`<div class="auriga-hub"></div>`).appendTo(page.main);
		this.inject_style();
		this.apply_theme();
	}

	show(project, view) {
		this.view = view === "health" ? "health" : "overview";
		this.page.clear_primary_action();
		this.page.clear_inner_toolbar();
		this.page.clear_menu();
		this.route_project = project;
		this.apply_theme();
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
			this.add_theme_menu();
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
		const health = this.view === "health" ? frappe.xcall(`${HUB_API}.get_project_health`, { project, period: this.get_period() }) : null;
		Promise.all([frappe.xcall(`${HUB_API}.get_project_hub`, { project }), health]).then(([data, health_data]) => {
			this.data = data;
			this.project = project;
			const info = data.project;
			this.page.set_title(`${info.project_name || info.name} (${info.tracker_identifier})`);
			this.page.set_indicator(__(info.status), info.status === "Open" ? "blue" : "gray");
			this.setup_actions(data);
			this.add_theme_menu();
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
		if (this.view === "health") {
			const range = __("Range");
			Object.entries(HUB_PERIODS).forEach(([key, text]) => {
				this.page.add_inner_button(
					`${this.get_period() === key ? "\u2713 " : "\u2003"}${__(text)}`,
					() => {
						this.set_flag("auriga_hub_period", key);
						this.show(this.project, "health");
					},
					range
				);
			});
		}
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
		["Work Item Summary", "Overdue Work Items", "Time Log Summary", "Release Progress", "Sprint Summary"].forEach((name) => {
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
		const tile = (value, label, cls, route) =>
			`<div class="hub-tile ${cls || ""}" ${route ? `data-route='${route}'` : ""}><b>${value}</b><span>${label}</span></div>`;
		const hours_label = (value, label) => tile(value, label, "hub-teal");
		const bars = (rows) => {
			const max = Math.max(1, ...rows.map((r) => r.count));
			return rows.length
				? rows.map((r) => `<div class="hub-bar"><span>${esc(__(r.label))}</span><div><i style="width:${(r.count / max) * 100}%"></i></div><b>${r.count}</b></div>`).join("")
				: `<div class="text-muted small">${__("Nothing open")}</div>`;
		};
		const sprint = d.active_sprint;
		const sprint_html = sprint
			? `<div class="hub-panel"><h6>${__("Active sprint")}: <a href="/desk/sprint/${encodeURIComponent(sprint.name)}">${esc(sprint.sprint_name)}</a></h6>
				<div class="text-muted small">${frappe.datetime.str_to_user(sprint.start_date)} - ${frappe.datetime.str_to_user(sprint.end_date)} · ${sprint.closed_items}/${sprint.total_items} ${__("closed")}</div>
				<div class="progress my-2"><div class="progress-bar" style="width:${flt(sprint.percent_complete)}%"></div></div>
				${sprint.goal ? `<div class="small">${esc(sprint.goal)}</div>` : ""}
				<div class="hub-chart"></div></div>`
			: `<div class="hub-panel"><h6>${__("Active sprint")}</h6><div class="text-muted small">${__("No sprint is running.")}</div></div>`;
		const table = (rows, head, cells) =>
			rows.length
				? `<table class="table table-sm hub-table"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map(cells).join("")}</tbody></table>`
				: `<div class="text-muted small">${__("None yet")}</div>`;
		const link = (doctype, name, label) => `<a href="/desk/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}">${esc(label || name)}</a>`;
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
				${tile(n.open, __("Open"), "hub-blue", "open")}${tile(n.overdue, __("Overdue"), "hub-red", "overdue")}
				${tile(n.mine, __("Assigned to me"), "hub-purple", "mine")}${tile(n.unassigned, __("Unassigned"), "hub-orange", "unassigned")}
				${tile(d.backlog_items, __("Backlog (no sprint)"), "hub-cyan", "backlog")}${tile(n.closed, __("Closed"), "hub-green", "closed")}
				${hours_label(n.hours_week, __("Hours this week"))}${hours_label(n.hours_total, __("Hours total"))}
			</div>
			<div class="hub-cols">
				<div class="hub-col">
					${sprint_html}
					<div class="hub-panel"><h6>${__("Recent work items")}</h6>${recent}</div>
				</div>
				<div class="hub-col">
					<div class="hub-panel"><h6>${__("Open by status")}</h6>${bars(d.by_status)}<h6 class="mt-3">${__("Open by type")}</h6>${bars(d.by_tracker)}</div>
					<div class="hub-panel"><h6>${__("Sprints")}</h6>${sprints}</div>
					<div class="hub-panel"><h6>${__("Releases")}</h6>${releases}</div>
					<div class="hub-panel"><h6>${__("Team")} (${d.members.length})</h6>${team}</div>
				</div>
			</div>`);
		this.$body.find(".hub-tile[data-route]").on("click", (e) => this.open_tile($(e.currentTarget).data("route")));
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
		if (["open", "overdue", "mine", "unassigned", "backlog"].includes(kind)) filters.is_closed = 0;
		if (kind === "closed") filters.is_closed = 1;
		if (kind === "overdue") filters.due_date = ["<", frappe.datetime.get_today()];
		if (kind === "mine") filters.assigned_to = frappe.session.user;
		if (kind === "unassigned") filters.assigned_to = ["is", "not set"];
		if (kind === "backlog") filters.sprint = ["is", "not set"];
		frappe.route_options = filters;
		frappe.set_route("List", "Work Item", "List");
	}

	set_flag(key, value) {
		try {
			localStorage.setItem(key, value ? String(value) : "");
		} catch (e) {
			/* storage blocked: the setting applies for this visit only */
		}
	}

	get_period() {
		try {
			const key = localStorage.getItem("auriga_hub_period");
			return HUB_PERIODS[key] ? key : "3m";
		} catch (e) {
			return "3m";
		}
	}

	chart(selector, config) {
		const el = this.$body.find(selector)[0];
		if (el) new frappe.Chart(el, { height: 230, ...config });
	}

	render_health(d, h) {
		const esc = frappe.utils.escape_html;
		const info = d.project;
		const f = h.flow;
		const t = h.time;
		const st = h.status;
		const per = h.bucket === "month" ? __("monthly") : __("weekly");
		const tile = (value, label, cls, sub) =>
			`<div class="hub-tile ${cls || ""}"><b>${value}</b><span>${label}</span>${sub ? `<em>${sub}</em>` : ""}</div>`;
		const reasons = st.reasons.map((r) => `<li class="hub-reason hub-${r.level}"><i></i>${esc(r.text)}</li>`).join("");
		const risk_badge = (r) => `<span class="hub-badge hub-risk-${r.risk}">${r.risk === "late" ? __("Late") : r.risk === "risk" ? __("At risk") : __("On track")}</span>`;
		const releases = h.releases.length
			? `<table class="table table-sm hub-table"><thead><tr><th>${__("Release")}</th><th>${__("Due")}</th><th>${__("Days left")}</th><th>${__("Progress")}</th><th></th></tr></thead><tbody>${h.releases
					.map(
						(r) => `<tr><td>${esc(r.label)}</td><td>${r.due_date ? frappe.datetime.str_to_user(r.due_date) : ""}</td><td>${r.days_left === null ? "" : r.days_left}</td>
						<td style="min-width:120px"><div class="progress"><div class="progress-bar" style="width:${flt(r.percent)}%"></div></div></td><td>${risk_badge(r)}</td></tr>`
					)
					.join("")}</tbody></table>`
			: `<div class="text-muted small">${__("No open releases")}</div>`;
		const bar = (label, value, max, cls) =>
			`<div class="hub-bar"><span>${esc(label)}</span><div><i class="${cls || ""}" style="width:${max ? (value / max) * 100 : 0}%"></i></div><b>${flt(value, 1)}</b></div>`;
		const hours_max = Math.max(t.estimated, t.spent, 1);
		// Stacked rows with full labels (charts truncate long names): [label, first, second] with two legend names.
		const stack = (rows, names, classes) => {
			const max = Math.max(1, ...rows.map((r) => r[1] + r[2]));
			const legend = `<div class="hub-legend"><span><i class="${classes[0]}"></i>${names[0]}</span><span><i class="${classes[1]}"></i>${names[1]}</span></div>`;
			return (
				legend +
				(rows.length
					? rows
							.map(
								(r) => `<div class="hub-stack"><span title="${esc(r[0])}">${esc(r[0])}</span><div>
								<i class="${classes[0]}" style="width:${(r[1] / max) * 100}%"></i><i class="${classes[1]}" style="width:${(r[2] / max) * 100}%"></i></div><b>${flt(r[1] + r[2], 1)}</b></div>`
							)
							.join("")
					: `<div class="text-muted small">${__("Nothing yet")}</div>`)
			);
		};
		const open_closed = `<div class="hub-meter"><i class="seg-blue" style="width:${f.total ? (f.open / f.total) * 100 : 0}%">${f.open}</i><i class="seg-green" style="width:${f.total ? (f.closed / f.total) * 100 : 0}%">${f.closed}</i></div>` +
			stack(f.by_tracker.map((r) => [__(r.label), r.open, r.closed]), [__("Open"), __("Closed")], ["seg-blue", "seg-green"]);
		const panel = (title, body, cls) => `<div class="hub-panel ${cls || ""}"><h6>${title}</h6>${body}</div>`;
		const people_panels =
			panel(__("Open tickets by person"), h.workload.length ? h.workload.map((w) => bar(w.name, w.open, Math.max(...h.workload.map((x) => x.open)))).join("") : `<div class="text-muted small">${__("Nothing open")}</div>`) +
			  panel(__("Hours by person (billable vs non-billable)"), stack(t.by_user.map((u) => [u.name, u.billable, u.non_billable]), [__("Billable"), __("Non-billable")], ["seg-green", "seg-orange"]));

		this.$body.html(`
			<div class="hub-title"><h4>${esc(info.project_name || info.name)}</h4><span class="hub-ident">${esc(info.tracker_identifier)}</span>
				<span class="text-muted">${__("Project health")} · ${__(HUB_PERIOD_NOTE[h.period])} · ${frappe.datetime.str_to_user(frappe.datetime.get_today())}</span></div>
			<div class="hub-status hub-${st.level}">
				<div class="hub-status-dial"><b>${st.score === null ? "-" : st.score}</b><span>${__("health score")}</span></div>
				<div><h5>${esc(st.label)}</h5><ul>${reasons}</ul></div>
			</div>
			<div class="hub-tiles">
				${tile(`${f.completion_pct}%`, __("Complete"), "hub-green", __("{0} of {1} tickets", [f.closed, f.total]))}
				${tile(f.open, __("Open tickets"), "hub-blue", __("{0} h estimated", [f.estimated_open_hours]))}
				${tile(f.closed, __("Closed tickets"), "hub-green", __("{0} h estimated", [f.estimated_closed_hours]))}
				${tile(`${f.overdue_pct}%`, __("Open & overdue"), f.overdue ? "hub-red" : "hub-teal", __("{0} tickets", [f.overdue]))}
				${tile(f.avg_resolution_days === null ? "-" : f.avg_resolution_days, __("Avg days to resolve"), "hub-purple")}
				${tile(t.spent, __("Hours spent"), "hub-cyan", t.burn_pct === null ? "" : __("{0}% of estimate", [t.burn_pct]))}
				${tile(t.billable, __("Billable hours"), "hub-teal", __("{0}% of spent", [t.billable_pct]))}
				${tile(t.non_billable, __("Non-billable hours"), "hub-orange")}
			</div>
			<div class="hub-cols hub-cols-even">
				<div class="hub-col">
					${panel(`${__("Tickets created vs resolved")} (${per})`, `<div class="hub-chart" id="hc-flow"></div><div class="small text-muted mt-2">${__("{0} created · {1} resolved in this range", [f.created_total, f.resolved_total])}</div>`)}
					${panel(__("Open vs closed (by type)"), open_closed)}
					${panel(`${__("Spent time: billable vs non-billable")} (${per})`, `<div class="hub-chart" id="hc-time"></div>`)}
					${panel(__("Hours by activity (billable vs non-billable)"), stack(t.by_activity.map((a) => [a.label, a.billable, a.non_billable]), [__("Billable"), __("Non-billable")], ["seg-green", "seg-orange"]))}
					${people_panels}
				</div>
				<div class="hub-col">
					${panel(`${__("Open backlog trend")} (${per})`, `<div class="hub-chart" id="hc-trend"></div>`)}
					${panel(__("Estimated vs spent hours"), `${bar(__("Estimated"), t.estimated, hours_max)}${bar(__("Spent"), t.spent, hours_max)}${bar(__("Billable"), t.billable, hours_max)}${bar(__("Non-billable"), t.non_billable, hours_max)}`)}
					${panel(__("Sprint velocity (tickets closed per completed sprint)"), h.velocity.length ? `<div class="hub-chart" id="hc-velocity"></div><div class="small text-muted mt-2">${__("Average {0} tickets / {1} hours per sprint", [flt(h.velocity.reduce((a, v) => a + v.items, 0) / h.velocity.length, 1), flt(h.velocity.reduce((a, v) => a + v.hours, 0) / h.velocity.length, 1)])}</div>` : `<div class="text-muted small">${__("No completed sprints yet")}</div>`)}
					${panel(__("Age of open tickets"), `<div class="hub-chart" id="hc-aging"></div>`)}
					${panel(__("Open tickets by priority"), `<div class="hub-chart" id="hc-priority"></div>`)}
					${panel(__("Releases"), releases)}
				</div>
			</div>`);

		const weeks = h.labels;
		const palette = { blue: "#3b82f6", green: "#10b981", orange: "#f59e0b", purple: "#8b5cf6", cyan: "#06b6d4", red: "#ef4444", pink: "#ec4899" };
		this.chart("#hc-flow", { type: "bar", data: { labels: weeks, datasets: [{ name: __("Created"), values: f.created }, { name: __("Resolved"), values: f.resolved }] }, colors: [palette.blue, palette.green], barOptions: { spaceRatio: 0.4 } });
		this.chart("#hc-trend", { type: "line", data: { labels: weeks, datasets: [{ name: __("Open at period end"), values: f.open_trend }] }, colors: [palette.purple], lineOptions: { regionFill: 1 } });
		this.chart("#hc-time", { type: "bar", data: { labels: weeks, datasets: [{ name: __("Billable"), values: t.billable_by_week }, { name: __("Non-billable"), values: t.non_billable_by_week }] }, colors: [palette.green, palette.orange], barOptions: { stacked: 1, spaceRatio: 0.4 } });
		if (h.velocity.length) this.chart("#hc-velocity", { type: "bar", data: { labels: h.velocity.map((v) => v.sprint), datasets: [{ name: __("Tickets closed"), values: h.velocity.map((v) => v.items) }] }, colors: [palette.purple], barOptions: { spaceRatio: 0.5 } });
		this.chart("#hc-aging", { type: "bar", data: { labels: f.aging.map((a) => a.label), datasets: [{ name: __("Open tickets"), values: f.aging.map((a) => a.count) }] }, colors: [palette.orange], barOptions: { spaceRatio: 0.5 } });
		if (f.open_by_priority.length) this.chart("#hc-priority", { type: "donut", data: { labels: f.open_by_priority.map((p) => __(p.label)), datasets: [{ values: f.open_by_priority.map((p) => p.count) }] }, colors: [palette.red, palette.orange, palette.blue, palette.green, palette.purple] });
	}

	get_theme() {
		let key = "glass";
		try {
			key = localStorage.getItem(HUB_THEME_KEY) || "glass";
		} catch (e) {
			/* storage blocked: keep the default */
		}
		return HUB_THEMES[key] ? key : "glass";
	}

	apply_theme() {
		this.$body.attr("data-hub-theme", this.get_theme());
	}

	add_theme_menu() {
		const current = this.get_theme();
		Object.entries(HUB_THEMES).forEach(([key, theme]) => {
			this.page.add_inner_button(
				`${key === current ? "\u2713 " : "\u2003"}${__(theme.label)}`,
				() => {
					try {
						localStorage.setItem(HUB_THEME_KEY, key);
					} catch (e) {
						/* storage blocked: the theme applies for this visit only */
					}
					this.show(this.route_project);  // rebuilds the page and the toolbar with the new theme
				},
				__("Theme")
			);
		});
	}

	inject_style() {
		$("#auriga-hub-style, #auriga-hub-style-v2, #auriga-hub-style-v3, #auriga-hub-style-v4").remove();
		if ($("#auriga-hub-style-v5").length) return;
		$(`<style id="auriga-hub-style-v5">
			${hub_theme_css()}
			.auriga-hub {
				--n-raised: var(--d) var(--d) calc(var(--d) * var(--bm)) var(--n-dark), calc(var(--d) * -1) calc(var(--d) * -1) calc(var(--d) * var(--bm)) var(--n-light);
				--n-soft: calc(var(--d) * .6) calc(var(--d) * .6) calc(var(--d) * var(--bm) * .6) var(--n-dark), calc(var(--d) * -.6) calc(var(--d) * -.6) calc(var(--d) * var(--bm) * .6) var(--n-light);
				--n-inset: inset calc(var(--d) * .45) calc(var(--d) * .45) calc(var(--d) * var(--bm) * .45) var(--n-dark), inset calc(var(--d) * -.45) calc(var(--d) * -.45) calc(var(--d) * var(--bm) * .45) var(--n-light);
				position: relative; overflow: hidden; border-radius: calc(var(--radius) + 4px); padding: 26px 24px 34px; margin: 6px 0 24px;
				color: var(--g-text);
				background: radial-gradient(520px 340px at 0% 0%, var(--g-blob1), transparent 70%), radial-gradient(560px 400px at 100% 100%, var(--g-blob3), transparent 70%), var(--g-bg);
			}
			.auriga-hub > * { position: relative; z-index: 1; }
			.auriga-hub .text-muted, .auriga-hub .small { color: var(--g-muted) !important; }
			.auriga-hub a { color: var(--acc); font-weight: 500; }

			.hub-title { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }
			.hub-title h4 { margin: 0; font-weight: 700; letter-spacing: -.01em; color: var(--g-text); }
			.hub-ident { font-size: 11px; font-weight: 600; letter-spacing: .04em; padding: 4px 12px; border-radius: 999px; color: var(--acc);
				background: var(--g-glass-strong); border: 1px solid var(--g-border); box-shadow: var(--n-soft); }
			.hub-warn { color: #b45309; }
			.hub-search { max-width: 380px; margin-bottom: 20px; }
			.hub-search input { border: 1px solid var(--g-border); border-radius: 999px; padding: 10px 18px; height: auto; color: var(--g-text);
				background: var(--g-glass); box-shadow: var(--n-inset); }

			.hub-card, .hub-panel {
				background: var(--g-glass); border: 1px solid var(--g-border); border-radius: var(--radius);
				-webkit-backdrop-filter: blur(var(--blur)) saturate(160%); backdrop-filter: blur(var(--blur)) saturate(160%);
				box-shadow: var(--n-raised);
			}
			.hub-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 22px; }
			.hub-card { padding: 18px 20px; cursor: pointer; transition: transform .18s ease; }
			.hub-card:hover, .hub-card:focus { transform: translateY(-3px); outline: none; }
			.hub-card-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 14px; font-size: 15px; }
			.hub-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center; margin-bottom: 14px; }
			.hub-stats > div { padding: 8px 2px; border-radius: calc(var(--radius) * .6); box-shadow: var(--n-inset); }
			.hub-stats b { display: block; font-size: 19px; font-weight: 700; }
			.hub-stats span, .hub-tile span { font-size: 11px; color: var(--g-muted); letter-spacing: .02em; }

			.hub-tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 18px; margin-bottom: 22px; }
			.hub-tile { --acc: #6366f1; padding: 16px 18px; border-radius: calc(var(--radius) * .9); background: var(--g-glass-strong); border: 1px solid var(--g-border);
				box-shadow: var(--n-raised); position: relative; transition: transform .15s ease; }
			.hub-tile::before { content: ""; position: absolute; left: 18px; top: 0; width: 34px; height: 4px; border-radius: 0 0 6px 6px; background: var(--acc); box-shadow: 0 2px calc(var(--bm) * 4px) var(--acc); }
			.hub-tile b { display: block; margin-top: 4px; font-size: 28px; font-weight: 700; line-height: 1.1; color: var(--acc); }
			.hub-tile[data-route] { cursor: pointer; } .hub-tile[data-route]:hover { transform: translateY(-2px); }
			.hub-tile[data-route]:active { transform: none; box-shadow: var(--n-inset); }
			.hub-blue { --acc: #3b82f6; } .hub-red { --acc: #ef4444; } .hub-purple { --acc: #8b5cf6; } .hub-orange { --acc: #f59e0b; }
			.hub-cyan { --acc: #06b6d4; } .hub-green { --acc: #10b981; } .hub-teal { --acc: #14b8a6; }
			.auriga-hub[data-hub-theme="mono"] .hub-tile { --acc: var(--g-text); }
			.auriga-hub[data-hub-theme="mono"] .hub-tile.hub-red b { text-decoration: underline; }

			.hub-cols { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 22px; }
			@media (max-width: 992px) { .hub-cols { grid-template-columns: 1fr; } .auriga-hub { padding: 18px 14px 26px; } }
			.hub-panel { padding: 18px 20px; margin-bottom: 22px; } .hub-panel h6 { margin: 0 0 12px; font-weight: 700; letter-spacing: .02em; color: var(--g-text); }

			.auriga-hub .progress, .hub-sprint .progress { height: 10px; border-radius: 999px; background: transparent; box-shadow: var(--n-inset); overflow: hidden; border: 1px solid var(--g-border); }
			.auriga-hub .progress-bar { border-radius: 999px; background: var(--bar); box-shadow: 0 0 calc(var(--bm) * 4px) var(--acc); }
			.hub-bar { display: grid; grid-template-columns: 104px 1fr 28px; align-items: center; gap: 10px; font-size: 12px; margin-bottom: 8px; }
			.hub-bar div { height: 9px; border-radius: 999px; box-shadow: var(--n-inset); overflow: hidden; border: 1px solid var(--g-border); }
			.hub-bar i { display: block; height: 100%; border-radius: 999px; background: var(--bar); }
			.hub-bar b { text-align: right; }

			.hub-table { font-size: 12px; margin: 0; color: var(--g-text); background: transparent; }
			.hub-table th { color: var(--g-muted); font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: .06em; border-top: 0; border-bottom: 1px solid var(--g-border); }
			.hub-table td { border-top: 1px solid var(--g-border); vertical-align: middle; }
			.hub-table tbody tr:hover { background: var(--g-glass-strong); }
			.hub-chart { margin-top: 6px; border-radius: calc(var(--radius) * .7); padding: 6px 4px 0; box-shadow: var(--n-inset); }
			.hub-chart text { fill: var(--g-muted); }

			.hub-tile em { display: block; font-style: normal; font-size: 10.5px; color: var(--g-muted); margin-top: 2px; }
			.hub-cols-even { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
			@media (max-width: 992px) { .hub-cols-even { grid-template-columns: 1fr; } }
			.hub-status { --lvl: #9ca3af; display: flex; gap: 22px; align-items: center; padding: 20px 24px; margin-bottom: 22px; border-radius: var(--radius);
				background: var(--g-glass); border: 1px solid var(--g-border); box-shadow: var(--n-raised); border-left: 6px solid var(--lvl);
				-webkit-backdrop-filter: blur(var(--blur)); backdrop-filter: blur(var(--blur)); }
			.hub-status.hub-green { --lvl: #10b981; } .hub-status.hub-amber { --lvl: #f59e0b; } .hub-status.hub-red { --lvl: #ef4444; }
			.hub-status-dial { flex: 0 0 auto; width: 92px; height: 92px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center;
				box-shadow: var(--n-inset); border: 4px solid var(--lvl); }
			.hub-status-dial b { font-size: 28px; line-height: 1; color: var(--lvl); } .hub-status-dial span { font-size: 9px; color: var(--g-muted); text-transform: uppercase; letter-spacing: .05em; }
			.hub-status h5 { margin: 0 0 8px; font-weight: 700; color: var(--lvl); font-size: 20px; }
			.hub-status ul { list-style: none; margin: 0; padding: 0; }
			.hub-reason { font-size: 13px; margin: 3px 0; display: flex; align-items: center; gap: 8px; }
			.hub-reason i { width: 8px; height: 8px; border-radius: 50%; background: #9ca3af; flex: 0 0 auto; }
			.hub-reason.hub-red i { background: #ef4444; } .hub-reason.hub-amber i { background: #f59e0b; } .hub-reason.hub-green i { background: #10b981; }
			.hub-meter { display: flex; height: 22px; border-radius: 999px; overflow: hidden; box-shadow: var(--n-inset); margin-bottom: 12px; border: 1px solid var(--g-border); }
			.hub-meter i, .hub-stack i { display: block; font-style: normal; font-size: 11px; font-weight: 700; color: #fff; text-align: center; line-height: 22px; min-width: 0; }
			.seg-blue { background: #3b82f6; } .seg-green { background: #10b981; } .seg-orange { background: #f59e0b; }
			.hub-legend { display: flex; gap: 16px; font-size: 11px; color: var(--g-muted); margin-bottom: 8px; }
			.hub-legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; }
			.hub-stack { display: grid; grid-template-columns: 150px 1fr 44px; align-items: center; gap: 10px; font-size: 12px; margin-bottom: 8px; }
			.hub-stack > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.hub-stack > div { display: flex; height: 12px; border-radius: 999px; overflow: hidden; box-shadow: var(--n-inset); border: 1px solid var(--g-border); }
			.hub-stack > div i { height: 100%; line-height: 12px; } .hub-stack b { text-align: right; }
			.hub-badge { font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: var(--g-glass-strong); border: 1px solid var(--g-border); }
			.hub-risk-late { color: #ef4444; } .hub-risk-risk { color: #f59e0b; } .hub-risk-ok { color: #10b981; }

			/* panels may take a pastel colour (bento themes define --p1..--p4; other themes fall back to the glass colour) */
			.hub-col > .hub-panel { background: var(--pp, var(--g-glass)); }
			.hub-col > .hub-panel:nth-child(4n+1) { --pp: var(--p1, var(--g-glass)); } .hub-col > .hub-panel:nth-child(4n+2) { --pp: var(--p2, var(--g-glass)); }
			.hub-col > .hub-panel:nth-child(4n+3) { --pp: var(--p3, var(--g-glass)); } .hub-col > .hub-panel:nth-child(4n) { --pp: var(--p4, var(--g-glass)); }

			/* flat family: no shadows, no gradients */
			.auriga-hub[data-hub-theme^="flat"] .hub-tile, .auriga-hub[data-hub-theme^="bento"] .hub-tile { box-shadow: none; }
			.auriga-hub[data-hub-theme^="flat"] .hub-tile::before, .auriga-hub[data-hub-theme^="bento"] .hub-tile::before { display: none; }
			.auriga-hub[data-hub-theme^="flat"] .hub-card:hover, .auriga-hub[data-hub-theme^="bento"] .hub-card:hover { transform: none; border-color: var(--acc); }
			.auriga-hub[data-hub-theme="flat-solid"] .hub-tile, .auriga-hub[data-hub-theme="bento-vivid"] .hub-tile { background: var(--acc); border-color: transparent; }
			.auriga-hub[data-hub-theme="flat-solid"] .hub-tile *, .auriga-hub[data-hub-theme="bento-vivid"] .hub-tile *,
			.auriga-hub[data-hub-theme="flat-solid"] .hub-tile b, .auriga-hub[data-hub-theme="bento-vivid"] .hub-tile b { color: #fff !important; }
			.auriga-hub[data-hub-theme="flat-tint"] .hub-tile, .auriga-hub[data-hub-theme="bento-pastel"] .hub-tile { background: color-mix(in srgb, var(--acc) 14%, var(--g-glass)); border-color: transparent; }
			.auriga-hub[data-hub-theme="flat-line"] .hub-tile { background: transparent; border: 2px solid var(--acc); }
			.auriga-hub[data-hub-theme="flat-line"] .hub-panel, .auriga-hub[data-hub-theme="flat-line"] .hub-card, .auriga-hub[data-hub-theme="flat-line"] .hub-status { border-width: 2px; }
			.auriga-hub[data-hub-theme="flat-solid"] .hub-status, .auriga-hub[data-hub-theme="flat-tint"] .hub-status, .auriga-hub[data-hub-theme="flat-line"] .hub-status { border-radius: var(--radius); }

			/* bento: a modular mosaic of rounded blocks of different sizes */
			.auriga-hub[data-hub-theme^="bento"] .hub-tiles { grid-template-columns: repeat(4, minmax(0, 1fr)); grid-auto-rows: minmax(96px, auto); gap: 14px; }
			.auriga-hub[data-hub-theme^="bento"] .hub-tile:first-child { grid-column: span 2; grid-row: span 2; display: flex; flex-direction: column; justify-content: flex-end; }
			.auriga-hub[data-hub-theme^="bento"] .hub-tile:first-child b { font-size: 54px; }
			.auriga-hub[data-hub-theme^="bento"] .hub-tile:nth-child(4) { grid-column: span 2; }
			.auriga-hub[data-hub-theme^="bento"] .hub-grid, .auriga-hub[data-hub-theme^="bento"] .hub-cols { gap: 14px; }
			.auriga-hub[data-hub-theme^="bento"] .hub-panel { margin-bottom: 14px; padding: 22px 24px; }
			.auriga-hub[data-hub-theme^="bento"] .hub-card, .auriga-hub[data-hub-theme^="bento"] .hub-status { border-color: transparent; }
			@media (max-width: 760px) { .auriga-hub[data-hub-theme^="bento"] .hub-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } .auriga-hub[data-hub-theme^="bento"] .hub-tile:nth-child(4) { grid-column: auto; } }
			@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) { .hub-card, .hub-panel { background: var(--g-glass-strong); } }
		</style>`).appendTo("head");
	}
}
