// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

/* global auri_pms */
// Health and cost view of every project the user manages (health, delivery, effort, risks, capacity): the Portfolio, shown as a tab of the
// Delivery & Health. Loaded on demand with frappe.require("auri_portfolio.bundle.js") after auri_hub.bundle.js.
frappe.provide("auri_pms");

(() => {
let ui; // shared UI kit (auri_hub.bundle.js)

class Portfolio {
	// ``page`` and ``$body`` belong to the host page (Delivery & Health); ``project`` (a name or a list) focuses it on those projects.
	constructor(page, $body, project) {
		ui = auri_pms.ui;
		this.page = page;
		this.$body = $body;
		this.applied = new Set([].concat(project || []));
		this.filter = "all";
		this.query = "";
		this.sort = { key: "level", asc: true };
	}

	// The host page owns the toolbar and the access check; this only draws the health and cost view into ``$body``.
	load(project) {
		if (project !== undefined) this.applied = new Set([].concat(project || []));
		ui.applyTheme(this.$body);
		this.$body.html(`<div class="text-muted p-4">${__("Loading...")}</div>`);
		frappe.xcall("auri_pms.auri_pms.api.get_portfolio", { period: ui.getPeriod() }).then((data) => {
			this.data = data;
			this.applied = new Set([...(this.applied || [])].filter((name) => data.projects.some((p) => p.name === name)));
			this.view = this.scoped_data();
			this.render();
		});
	}

	render() {
		const d = this.view;
		const k = d.kpis;
		const esc = ui.esc;
		const { tile, panel, stack, bar } = ui;
		const today = frappe.datetime.get_today();
		const clamp = (v) => Math.max(0, Math.min(100, Math.round(v)));
		// the health verdict is only shown for projects whose owner ticked "Show on Portfolio"
		this.show_health = k.red + k.amber + k.green + k.none > 0;
		if (!this.show_health) this.filter = "all";
		const projects = d.projects;
		const visible = projects.filter((p) => !p.health_hidden && p.level !== "none");
		const worst = visible.find((p) => p.level === "red") ? "red" : visible.find((p) => p.level === "amber") ? "amber" : visible.length ? "green" : "none";
		const attention = visible.filter((p) => p.level === "red" || p.level === "amber");
		const verdict = !visible.length ? "" : worst === "green" ? __("All {0} projects are On Track", [visible.length]) : attention.length <= 2 ? __("Attention needed on {0}", [attention.map((p) => p.project_name).join(", ")]) : __("Attention needed on {0} of {1} projects", [attention.length, visible.length]);
		const score = visible.length ? k.avg_score : null;
		const total = k.open + k.closed;
		const complete = total ? clamp((k.closed / total) * 100) : null;
		const overdue_pct = k.open ? Math.round((k.overdue / k.open) * 100) : 0;
		const cap = d.capacity || { people: [], over_allocated: 0, burnout: 0 };

		// ---- one line that says it all, with the project counts that filter the table below
		const applied_bar = this.applied.size
			? `<div class="hub-panel pf-applied"><span class="pf-applied-lead">${__("Showing only")}</span>${[...this.applied].map((name) => {
					const p = this.data.projects.find((x) => x.name === name);
					return p ? `<span class="pf-scope-chip" data-project="${esc(name)}">${esc(p.project_name)} <i>✕</i></span>` : "";
				}).join("")}<span class="pf-applied-n">${__("{0} of {1} projects · the other projects are hidden", [this.applied.size, this.data.projects.length])}</span><button class="btn btn-primary btn-sm pf-applied-clear">${__("Show all")}</button></div>`
			: "";
		const header = `<div class="hub-title"><h4>${__("Health and cost")}</h4><span class="text-muted">${k.projects === 1 ? __("1 project") : __("{0} projects", [k.projects])} · ${__(ui.PERIOD_NOTE[d.period])} · ${frappe.datetime.str_to_user(today)}</span></div>
			${applied_bar}
			${verdict ? `<div class="hub-panel pf-verdict pf-v-${worst}"><i></i><b>${esc(verdict)}</b>
				<div class="pf-split-chips"><span class="pf-chip-red" data-filter="red"><b>${k.red}</b>${__("Off Track")}</span><span class="pf-chip-amber" data-filter="amber"><b>${k.amber}</b>${__("At Risk")}</span><span class="pf-chip-green" data-filter="green"><b>${k.green}</b>${__("On Track")}</span></div></div>` : ""}`;

		// ---- the dials: health, delivery, money, time
		const ring = (value, label, sub, tone, target) => `<div class="hub-panel ph3-gauge ph2-in" ${target ? ui.goAttr(target) : ""}>
			<div class="ph2-ring ph3-ring ${tone || ""}" style="--p:${value === null ? 0 : value}">
				<svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="ph2-ring-bg"/><circle cx="60" cy="60" r="52" class="ph2-ring-fg" pathLength="100"/></svg>
				<div><div class="ph2-ring-num"><b>${value === null ? "–" : value}</b>${value === null ? "" : "<span>%</span>"}</div></div>
			</div><strong>${label}</strong><small>${sub || ""}</small></div>`;
		const rings = [
			visible.length ? ring(score, __("Health score"), this.show_health ? `${k.red} ${__("Off Track")} · ${k.amber} ${__("At Risk")} · ${k.green} ${__("On Track")}` : "", worst === "red" ? "g-red" : worst === "amber" ? "g-orange" : "g-green") : "",
			ring(complete, __("Complete"), __("{0} of {1} tickets", [k.closed, total]), "g-green", ui.go("Work Item", { is_closed: 1 })),
			ring(k.burn_pct === null ? null : clamp(k.burn_pct), __("Budget burn"), __("hours spent / budget (or estimate)"), k.burn_pct !== null && k.burn_pct > 100 ? "g-red" : "g-blue", ui.go("Time Entry")),
			ring(clamp(k.billable_pct), __("Billable"), `${k.hours_spent} ${__("h in total")}`, "g-teal", ui.go("Time Entry", { is_billable: 1 })),
		].filter(Boolean);
		const gauges = `<div class="ph3-gauges" style="--n:${rings.length}">${rings.join("")}</div>`;

		// ---- the numbers: the theme's coloured tiles
		const kpis = `<div class="hub-tiles">
			${tile(k.projects, __("Projects"), "hub-blue", this.show_health ? `${k.red} ${__("Off Track")} · ${k.amber} ${__("At Risk")} · ${k.green} ${__("On Track")}` : "", ui.go("Project", { tracker_identifier: ["is", "set"] }))}
			${tile(k.open, __("Open tickets"), "hub-purple", k.client_dependent ? `${k.client_dependent} ${__("waiting on client")}` : "", ui.go("Work Item", { is_closed: 0 }))}
			${tile(k.overdue, __("Overdue"), k.overdue ? "hub-red" : "hub-teal", __("{0}% of open", [overdue_pct]), ui.go("Work Item", { is_closed: 0, due_date: ["<", today] }))}
			${tile(k.client_dependent, __("Waiting on client"), k.client_dependent ? "hub-orange" : "hub-teal", "", ui.goReport("Client Dependencies"))}
			${tile(k.closed, __("Closed tickets"), "hub-green", "", ui.go("Work Item", { is_closed: 1 }))}
			${tile(k.hours_period, __("Hours in range"), "hub-teal", `${k.hours_spent} ${__("h in total")}`, ui.go("Time Entry", { date: [">=", d.range_start] }))}
			${tile(k.risks_open, __("Open risks"), k.risks_critical ? "hub-red" : "hub-orange", `${k.risks_critical} ${__("critical")} · ${k.risks_high} ${__("high")}`, ui.go("Risk Register", { status: ["in", ui.OPEN_RISK] }))}
			${tile(cap.over_allocated, __("Over-allocated people"), cap.over_allocated ? "hub-orange" : "hub-green", `${cap.burnout} ${__("burnout risk")}`, ui.go("Project", { pms_enabled: 1 }))}
		</div>`;

		// ---- a card per project, worst first: the status of every project at a glance
		const cards = projects.map((p, i) => {
			const total_p = p.open + p.closed;
			const done = total_p ? clamp((p.closed / total_p) * 100) : 0;
			const on_time = Math.max(0, p.open - p.overdue);
			const wi = (extra) => ui.go("Work Item", { project: p.name, ...extra });
			const te = (extra) => ui.go("Time Entry", { project: p.name, ...extra });
			const stat = (value, label, tone, target) => `<div class="${tone || ""} ${target ? "pf-click" : ""}" ${target ? ui.goAttr(target) : ""}><b>${value}</b><span>${label}</span></div>`;
			return `<div class="hub-panel pf-card ph2-in" data-project="${esc(p.name)}" tabindex="0" style="animation-delay:${i * 30}ms">
				<div class="pf-card-top">
					<div class="pk-ring" style="--p:${done}"><svg viewBox="0 0 44 44"><circle cx="22" cy="22" r="18" class="pk-ring-bg"/><circle cx="22" cy="22" r="18" class="pk-ring-fg" pathLength="100"/></svg><b>${done}<small>%</small></b></div>
					<div class="pk-name"><b>${esc(p.project_name)}</b><small><span class="pk-ident">${esc(p.identifier)}</span>${p.sprint ? `${esc(p.sprint.label)} · ${flt(p.sprint.percent, 0)}%` : ""}</small></div>
					${p.health_hidden || p.level === "none" ? "" : `<span class="pf-health pf-${p.level}" title="${esc(p.headline)}"><i></i>${esc(p.label)}${p.score === null ? "" : ` <b>${p.score}</b>`}</span>`}
				</div>
				${total_p ? `<div class="pk-split" title="${__("{0} closed · {1} open · {2} overdue", [p.closed, on_time, p.overdue])}"><i class="pk-closed" style="flex:${p.closed}"></i><i class="pk-open" style="flex:${on_time}"></i><i class="pk-over" style="flex:${p.overdue}"></i></div>` : `<div class="pk-split pk-empty"></div>`}
				<div class="pf-card-nums">
					${stat(p.open, __("Open"), "", wi({ is_closed: 0 }))}${stat(`${p.overdue_pct}%`, __("Overdue"), p.overdue_pct > 25 ? "pf-bad" : "", wi({ is_closed: 0, due_date: ["<", today] }))}${stat(p.burn_pct === null ? "–" : `${p.burn_pct}%`, __("Burn"), p.burn_pct > 100 ? "pf-bad" : "", te())}${stat(`${p.billable_pct}%`, __("Billable"), "", te({ is_billable: 1 }))}
					${stat(p.closed, __("Closed"), "", wi({ is_closed: 1 }))}${stat(p.client_dependent || "–", __("Client"), p.client_dependent ? "pf-warn" : "", p.client_dependent ? wi({ is_closed: 0, dependent_on_client: 1 }) : null)}${stat(p.risks_open ? p.risks_open + (p.risks_critical ? ` (${p.risks_critical})` : "") : "–", __("Risks"), p.risks_critical ? "pf-bad" : "", p.risks_open ? ui.go("Risk Register", { project: p.name, status: ["in", ui.OPEN_RISK] }) : null)}${stat(p.hours_period, __("Hours"), "", te({ date: [">=", d.range_start] }))}
				</div>
				<div class="pf-card-foot">${this.note_foot(p)}</div></div>`;
		});
		const glance = `<div class="pf-sec"><h5>${__("Projects at a glance")}</h5><span>${__("worst first · click a project for its health report")}</span></div><div class="pf-cards">${cards.join("")}</div>`;

		// ---- why: every reason of every project with its points, and how the score is worked out
		const reason_rank = { red: 0, amber: 1, info: 2, green: 3 };
		const groups = visible.map((p) => {
			const list = (p.reason_list || []).slice().sort((a, b) => (reason_rank[a.level] ?? 2) - (reason_rank[b.level] ?? 2));
			return `<div class="pf-why-project"><div class="pf-why-head"><b>${esc(p.project_name)}</b><span class="pf-health pf-${p.level}"><i></i>${esc(p.label)} <b>${p.score}</b></span></div>
				${list.map((r) => `<div class="pf-reason pf-r-${r.level}" ${r.link ? ui.goAttr(r.link) : ""}><i></i><span>${esc(r.text)}</span>${p.calc && (r.level === "red" || r.level === "amber") ? `<b>−${r.level === "red" ? p.calc.red_penalty : p.calc.amber_penalty}</b>` : ""}</div>`).join("")}</div>`;
		});
		const calc = (visible.find((p) => p.calc) || {}).calc || null;
		const calc_lines = [...visible.map((p) => `${p.project_name}: ${ui.scoreCalc(p.calc, p.score)}`), ...(visible.length > 1 ? [__("Average of {0} projects = {1}", [visible.length, k.avg_score])] : [])];
		const why = visible.length
			? `<details class="pf-fold"><summary class="pf-sec"><h5>${__("Why this status")}</h5><span>${__("each reason takes points off the score")}</span><i class="pf-chev"></i></summary>
				<div class="hub-panel pf-why"><div class="pf-why-grid">${groups.join("")}</div>
				<div class="pf-calc"><b>${__("How the score is worked out")}</b>${calc_lines.map((l) => `<span>${esc(l)}</span>`).join("")}
				${calc ? `<small>${esc(__("The score starts at 100. Each Off Track (red) reason takes off {0} points (PMS Settings: Health Score Penalty per Off Track Reason) and each At Risk (amber) reason takes off {1} (Health Score Penalty per At Risk Reason).", [calc.red_penalty, calc.amber_penalty])).replace("PMS Settings", `<a href="/desk/pms-settings">PMS Settings</a>`)}</small>` : ""}</div></div></details>`
			: "";

		this.selected = new Set();

		this.$body.html(`<div class="ph2 ph3 pf">
			${header}
			${gauges}
			${kpis}
			${glance}
			${why}
			${this.trend_panel()}
			<div class="pf-sec"><h5>${__("Details")}</h5><span>${__("click a project in the table, or use the filters, to focus everything below")}</span></div>
			<div class="hub-panel pf-projects ph2-in"><h6>${__("Projects")}${ui.viewAll(ui.go("Project", { pms_enabled: 1 }))}</h6>
				<div class="hub-toolbar"><div class="hub-search"><input type="text" class="form-control" placeholder="${__("Search or pick a project")}" value="${esc(this.query)}" autocomplete="off"><div class="pf-suggest"></div></div></div>
				${this.show_health ? `<div class="hub-chips">${[["all", __("All")], ["red", __("Off Track")], ["amber", __("At Risk")], ["green", __("On Track")]].map(([key, text]) => `<span class="hub-chip ${this.filter === key ? "active" : ""}" data-filter="${key}">${text}</span>`).join("")}</div>` : ""}
				<div class="hub-projects" style="overflow-x:auto"></div></div>
			<div class="pf-scope"></div>
			<div class="pf-below"></div>
		</div>`);
		ui.bindTiles(this.$body);
		this.bind_notes(this.$body);
		this.$body.find(".pf-applied .pf-scope-chip").on("click", (e) => {
			const name = $(e.currentTarget).data("project");
			this.set_applied([...this.applied].filter((x) => x !== name));
		});
		this.$body.find(".pf-applied-clear").on("click", () => this.set_applied([]));
		this.$body.find(".pf-card").on("click keypress", (e) => {
			if (e.type === "keypress" && e.key !== "Enter") return;
			if ($(e.target).closest(".pf-note-btn").length) return;
			frappe.set_route("project-hub", $(e.currentTarget).data("project"), "health");
		});
		this.$body.find(".pf-split-chips span").on("click", (e) => {
			this.set_filter($(e.currentTarget).data("filter"));
			this.$body.find(".pf-projects")[0].scrollIntoView({ behavior: "smooth", block: "start" });
		});
		this.$body.find(".hub-search input").on("input", (e) => {
			this.query = $(e.target).val();
			this.render_table();
			this.render_below();
		});
		this.$body.find(".hub-chip").on("click", (e) => this.set_filter($(e.currentTarget).data("filter")));
		this.render_table();
		this.render_below();
		this.bind_suggest();
		this.bind_trend();
	}

	// The data of the applied projects only (all of them when nothing is applied): the list, the totals and the team.
	scoped_data() {
		const full = this.data;
		if (!this.applied.size) return full;
		const projects = full.projects.filter((p) => this.applied.has(p.name));
		const sum = (key) => projects.reduce((t, p) => t + flt(p[key]), 0);
		const spent = sum("hours_spent");
		const basis = projects.reduce((t, p) => t + (flt(p.budget) || flt(p.estimated)), 0);
		const billable = projects.reduce((t, p) => t + (flt(p.hours_spent) * flt(p.billable_pct)) / 100, 0);
		const scores = projects.filter((p) => p.score !== null && p.score !== undefined).map((p) => p.score);
		const kpis = {
			...full.kpis,
			projects: projects.length,
			red: projects.filter((p) => p.level === "red").length,
			amber: projects.filter((p) => p.level === "amber").length,
			green: projects.filter((p) => p.level === "green").length,
			none: projects.filter((p) => p.level === "none" && !p.health_hidden).length,
			hidden: projects.filter((p) => p.health_hidden).length,
			risks_open: sum("risks_open"),
			risks_critical: sum("risks_critical"),
			risks_high: sum("risks_high"),
			open: sum("open"),
			closed: sum("closed"),
			overdue: sum("overdue"),
			client_dependent: sum("client_dependent"),
			hours_spent: flt(spent, 2),
			hours_period: flt(sum("hours_period"), 2),
			billable_pct: spent ? flt((billable * 100) / spent, 1) : 0,
			burn_pct: basis ? flt((spent * 100) / basis, 1) : null,
			avg_score: scores.length ? Math.floor(scores.reduce((t, v) => t + v, 0) / scores.length + 0.5) : 0,
		};
		const c = full.capacity;
		const people = c ? c.people.filter((m) => m.member_of.some((name) => this.applied.has(name))) : [];
		const capacity = c && {
			...c,
			people,
			over_allocated: people.filter((m) => m.over_allocated).length,
			burnout: people.filter((m) => m.burnout).length,
		};
		return { ...full, projects, kpis, capacity };
	}

	// Apply a project filter: the whole page shows those projects only, until "Show all".
	set_applied(names) {
		this.applied = new Set(names);
		this.view = this.scoped_data();
		this.query = "";
		this.filter = "all";
		this.render();
		window.scrollTo({ top: 0 });
	}

	// ---- notes on a project (comments on the Project, so they also show on the project's own page); the dialog is shared with Project Health
	note_button(p) {
		return ui.noteButton(p);
	}

	note_foot(p) {
		return ui.noteFoot(p);
	}

	bind_notes($root) {
		ui.bindNotes($root, (name) => this.open_notes(name));
	}

	open_notes(project) {
		const p = this.data.projects.find((x) => x.name === project);
		ui.openNotes(project, p.project_name, (notes) => this.set_notes(p, notes));
	}

	// keep the counts and the latest note on the cards and in the table in step with what was just added
	set_notes(p, notes) {
		p.notes = { count: notes.length, last: notes[0] ? { text: notes[0].text, by_name: notes[0].by_name || notes[0].by, on: notes[0].on } : null };
		const $card = this.$body.find(`.pf-card[data-project="${p.name}"] .pf-card-foot`).html(this.note_foot(p));
		this.bind_notes($card);
		this.render_table();
		this.draw_ticket_table(this.scoped().scope);
	}

	// The projects the table currently lists (status chips and search), and the part of them that is focused by a click.
	scoped() {
		const q = this.query.toLowerCase();
		const rows = this.view.projects.filter((p) => (this.filter === "all" || p.level === this.filter) && `${p.project_name} ${p.identifier}`.toLowerCase().includes(q));
		const chosen = rows.filter((p) => this.selected.has(p.name));
		return { rows, scope: chosen.length ? chosen : rows, focused: chosen.length > 0 };
	}

	// Everything under the table, for the focused projects only (all listed projects when none is clicked).
	render_below() {
		const d = this.view;
		const k = d.kpis;
		const esc = ui.esc;
		const { bar, panel, stack } = ui;
		const all = d.projects;
		const { rows, scope, focused } = this.scoped();
		const filtered = scope.length < all.length;

		// the line that says what the panels below show
		const $scope = this.$body.find(".pf-scope");
		$scope.toggleClass("on", filtered);
		$scope.html(focused
			? `<span>${__("Showing")}</span>${scope.map((p) => `<span class="pf-scope-chip" data-project="${esc(p.name)}">${esc(p.project_name)} <i>✕</i></span>`).join("")}<a class="pf-scope-clear">${__("Show all")}</a>`
			: filtered
				? `<span>${__("Showing {0} of {1} projects", [scope.length, all.length])} · ${__("filtered by the status or search above")}</span>`
				: `<span>${this.applied.size ? __("The {0} applied projects", [all.length]) : __("All {0} projects", [all.length])} · ${__("click a project in the table to focus everything below")}</span>`);
		$scope.find(".pf-scope-chip").on("click", (e) => {
			this.selected.delete($(e.currentTarget).data("project"));
			this.render_table();
			this.render_below();
		});
		$scope.find(".pf-scope-clear").on("click", () => {
			this.selected.clear();
			this.render_table();
			this.render_below();
		});

		const $below = this.$body.find(".pf-below");
		if (!scope.length) {
			$below.html(`<div class="hub-panel ph2-empty">${__("No project matches the filter.")}</div>`);
			return;
		}
		const sum = (key) => d.labels.map((_l, i) => scope.reduce((t, p) => t + flt((p.trend || {})[key] ? p.trend[key][i] : 0, 2), 0));
		const risky = scope.filter((p) => p.risks_open);
		const burn_max = Math.max(100, ...scope.map((x) => x.burn_pct || 0));

		// rows with the bar and, next to it, the count of every part
		const counted = (rows, names, classes, routes, parts) => {
			const max = Math.max(1, ...rows.map((r) => r.slice(1).reduce((a, b) => a + b, 0)));
			return `<div class="hub-legend">${names.map((n, i) => `<span><i class="${classes[i]}"></i>${n}</span>`).join("")}</div>`
				+ rows.map((r, k) => `<div class="pf-cstack" ${routes[k] ? ui.goAttr(routes[k]) : ""}><span title="${esc(r[0])}">${esc(r[0])}</span><b>${r.slice(1).reduce((a, b) => a + b, 0)}</b>
					<div class="pf-cbar">${r.slice(1).map((v, i) => `<i class="${classes[i]}" style="width:${(v / max) * 100}%"></i>`).join("")}</div>
					<span class="pf-counts">${r.slice(1).map((v, i) => `<em class="${classes[i]} ${v ? "" : "zero"}" title="${names[i]}" ${v && parts && parts[k] && parts[k][i] ? ui.goAttr(parts[k][i]) : ""}>${v}</em>`).join("")}</span></div>`).join("");
		};
		const p_tickets = panel(__("Tickets by project") + ui.viewAll(ui.go("Work Item", {})), counted(scope.slice(0, 12).map((p) => [p.project_name, p.open - p.client_dependent, p.client_dependent, p.closed]), [__("Open (with us)"), __("Waiting on client"), __("Closed")], ["seg-blue", "seg-orange", "seg-green"], scope.slice(0, 12).map((p) => ui.go("Work Item", { project: p.name })),
			scope.slice(0, 12).map((p) => [ui.go("Work Item", { project: p.name, is_closed: 0, dependent_on_client: 0 }), ui.go("Work Item", { project: p.name, is_closed: 0, dependent_on_client: 1 }), ui.go("Work Item", { project: p.name, is_closed: 1 })])), "ph2-card");
		const p_flow = panel(`${__("Tickets created vs resolved")} (${d.bucket === "month" ? __("monthly") : __("weekly")})${ui.viewAll(ui.go("Work Item", {}))}`, `<div class="hub-chart" id="pf-flow"></div>`, "ph2-card");
		const p_risks = risky.length ? panel(__("Open risks by project") + ui.viewAll(ui.go("Risk Register", { status: ["in", ui.OPEN_RISK] })), counted(risky.slice(0, 12).map((p) => [p.project_name, p.risks_critical, p.risks_high, p.risks_open - p.risks_critical - p.risks_high]), [__("Critical"), __("High"), __("Medium / Low")], ["seg-red", "seg-orange", "seg-yellow"], risky.slice(0, 12).map((p) => ui.go("Risk Register", { project: p.name, status: ["in", ui.OPEN_RISK] })),
			risky.slice(0, 12).map((p) => ["Critical", "High"].map((level) => ui.go("Risk Register", { project: p.name, risk_level: level, status: ["in", ui.OPEN_RISK] })).concat([ui.go("Risk Register", { project: p.name, risk_level: ["in", ["Medium", "Low"]], status: ["in", ui.OPEN_RISK] })]))), "ph2-card") : "";
		const p_burn = panel(__("Budget burn by project") + ui.viewAll(ui.go("Time Entry", {})), `<div class="pf-note">${__("% of budget, or of the estimate when there is no budget")}</div>` + (scope.filter((p) => p.burn_pct !== null).map((p) => bar(p.project_name, p.burn_pct, burn_max, p.burn_pct > 100 ? "seg-red" : "")).join("") || `<div class="text-muted small">${__("No estimates yet")}</div>`), "ph2-card");

		// billing: hours and tickets, and the time by ticket category (the panels are shared with Project Health)
		const scope_names = scope.map((p) => p.name);
		const { bill, cats } = ui.mergeBilling(scope.map((p) => p.billing));
		const p_tk = ui.billableTicketsPanel(bill, ["in", scope_names]);
		const category = ui.categoryPanel(cats, ["in", scope_names]);
		const p_cat = category.html;
		const p_bill = ui.billingPanel(["in", scope_names]);

		$below.html(`<div class="ph2-grid ph2-grid-2">${p_flow}${p_bill}</div>
			<div class="ph2-grid ph2-grid-2">${[p_tickets, p_risks].filter(Boolean).join("")}</div>
			<div class="ph2-grid ph2-grid-3">${p_tk}${p_cat}${p_burn}</div>
			${this.capacity_panel(filtered ? scope.map((p) => p.name) : this.applied.size ? [...this.applied] : null)}
			<div class="hub-panel ph2-card pf-tkt"><h6>${__("Tickets and billable time by period")}${ui.viewAll(ui.go("Work Item", {}))}</h6>
				<div class="pf-tkt-tools"></div><div class="pf-tkt-body"></div>
				<div class="pf-note pf-tkt-note">${__("Created and Closed count the tickets created and closed in the period; In progress and Waiting on client count the open tickets created in the period that are in progress or waiting on the client now. Billable time and Actual spent are the hours logged in the period (Actual spent = billable + non-billable).")}</div></div>`);
		this.draw_ticket_table(scope);
		const palette = ui.PALETTE;
		const axis = { xIsSeries: 1, xAxisMode: "tick" };
		ui.chart(this.$body, "#pf-flow", { type: "bar", data: { labels: d.labels, datasets: [{ name: __("Created"), values: sum("created") }, { name: __("Resolved"), values: sum("resolved") }] }, colors: [palette.blue, palette.green], barOptions: { spaceRatio: 0.4 }, axisOptions: axis }, (i) => {
			const [from, to] = this.bucket(i);
			ui.openTarget(ui.go("Work Item", { project: ["in", scope_names], creation: ["between", [from, to]] }));
		});
		ui.drawBilling($below, { labels: d.labels, starts: this.data.starts, billable: sum("billable"), non_billable: sum("non_billable"), project: ["in", scope_names] });
		category.bind($below);
		ui.bindTiles($below);
	}

	// The search box lists every project that has Auri PMS switched on: tick one or several and press Apply to focus everything below.
	bind_suggest() {
		const esc = ui.esc;
		const $input = this.$body.find(".pf-projects .hub-search input");
		const $list = this.$body.find(".pf-suggest");
		let pending = new Set(this.applied);
		const draw = () => {
			const q = $input.val().toLowerCase();
			const rows = this.data.projects.filter((p) => `${p.project_name} ${p.identifier}`.toLowerCase().includes(q));
			$list.html(`<div class="pf-sug-head">${__("Projects with Auri PMS switched on")} · ${this.data.projects.length}</div>`
				+ (rows.length
					? rows.map((p) => `<div class="pf-sug ${pending.has(p.name) ? "on" : ""}" data-project="${esc(p.name)}"><i class="pf-sug-check"></i><b>${esc(p.project_name)}</b><span class="pf-ident">${esc(p.identifier)}</span>
						${!p.health_hidden && p.level !== "none" ? `<span class="pf-health pf-${p.level}"><i></i>${esc(p.label)}</span>` : `<small>${__("{0} open", [p.open])}</small>`}</div>`).join("")
					: `<div class="pf-sug-empty">${__("No project matches")}</div>`)
				+ `<div class="pf-sug-foot"><a class="pf-sug-clear">${__("Clear")}</a><button class="btn btn-primary btn-sm pf-sug-apply">${pending.size ? __("Apply ({0})", [pending.size]) : __("Show all projects")}</button></div>`);
		};
		const close = () => $list.removeClass("open");
		const apply = () => {
			close();
			$input.val("").blur();
			this.set_applied(pending);
		};
		$input.on("focus click input", () => {
			if (!$list.hasClass("open")) pending = new Set(this.applied);
			draw();
			$list.addClass("open");
		});
		$input.on("blur", () => setTimeout(close, 120));
		$input.on("keydown", (e) => {
			if (e.key === "Escape") close();
			if (e.key === "Enter") {
				e.preventDefault();
				apply();
			}
		});
		$list.on("mousedown", (e) => e.preventDefault()); // clicking the list keeps the focus, so several projects can be ticked
		$list.on("click", ".pf-sug", (e) => {
			const name = $(e.currentTarget).data("project");
			if (pending.has(name)) pending.delete(name);
			else pending.add(name);
			draw();
		});
		$list.on("click", ".pf-sug-clear", () => {
			pending.clear();
			draw();
		});
		$list.on("click", ".pf-sug-apply", apply);
	}

	// The first and last day of period ``i`` of the Portfolio (a week, or a month on long ranges).
	bucket(i) {
		const starts = this.data.starts;
		return [starts[i], i + 1 < starts.length ? frappe.datetime.add_days(starts[i + 1], -1) : frappe.datetime.get_today()];
	}

	// The final table: tickets created, closed and in progress per project for a period (overall by default).
	// The numbers come from the server for the chosen period; the rows follow the focused projects.
	draw_ticket_table(scope) {
		const esc = ui.esc;
		const $panel = this.$body.find(".pf-tkt");
		if (!$panel.length) return;
		const today = frappe.datetime.get_today();
		const tk = (this.tk = this.tk || { key: "all", from: frappe.datetime.add_days(today, -29), to: today, rows: null });
		const options = [["all", __("Overall")], ["7", __("Last 7 days")], ["30", __("Last 30 days")], ["90", __("Last 90 days")], ["year", __("This year")], ["custom", __("Custom range")]];
		const range = () => {
			if (tk.key === "all") return {};
			if (tk.key === "custom") return { from_date: tk.from, to_date: tk.to };
			if (tk.key === "year") return { from_date: `${today.slice(0, 4)}-01-01`, to_date: today };
			return { from_date: frappe.datetime.add_days(today, -(+tk.key - 1)), to_date: today };
		};
		const load = () => {
			tk.rows = null;
			this.draw_ticket_table(this.scoped().scope);
			frappe.xcall("auri_pms.auri_pms.api.get_portfolio_tickets", range()).then((rows) => {
				tk.rows = rows;
				this.draw_ticket_table(this.scoped().scope);
			});
		};
		$panel.find(".pf-tkt-tools").html(`<div class="pf-tabs">${options.map(([key, label]) => `<span class="${tk.key === key ? "active" : ""}" data-key="${key}">${label}</span>`).join("")}</div>
			${tk.key === "custom" ? `<div class="pf-tkt-dates"><input type="date" class="form-control" value="${tk.from}" data-edge="from"><span>→</span><input type="date" class="form-control" value="${tk.to}" data-edge="to"></div>` : ""}`);
		$panel.find(".pf-tabs span").on("click", (e) => {
			tk.key = $(e.currentTarget).data("key");
			load();
		});
		$panel.find(".pf-tkt-dates input").on("change", (e) => {
			tk[$(e.currentTarget).data("edge")] = $(e.currentTarget).val() || tk[$(e.currentTarget).data("edge")];
			load();
		});
		const $body = $panel.find(".pf-tkt-body");
		if (!tk.rows) {
			$body.html(`<div class="text-muted small">${__("Loading...")}</div>`);
			if (!tk.loading) {
				tk.loading = true;
				frappe.xcall("auri_pms.auri_pms.api.get_portfolio_tickets", range()).then((rows) => {
					tk.loading = false;
					tk.rows = rows;
					this.draw_ticket_table(this.scoped().scope);
				});
			}
			return;
		}
		const names = new Set(scope.map((p) => p.name));
		const rows = tk.rows.filter((r) => names.has(r.project));
		const sum = (key) => rows.reduce((t, r) => t + flt(r[key]), 0);
		const total = { created: sum("created"), closed: sum("closed"), in_progress: sum("in_progress"), client_dependent: sum("client_dependent"), billable_hours: sum("billable_hours"), spent_hours: sum("spent_hours") };
		const dr = range();
		const between = (field) => (dr.from_date ? { [field]: ["between", [dr.from_date, dr.to_date]] } : {});
		const wi = (project, extra) => ui.go("Work Item", { project, ...extra });
		const te = (project, extra) => ui.go("Time Entry", { project, ...extra });
		const cell = (value, cls, target) => `<td><span class="pf-tkn ${cls} ${value ? "" : "zero"}" ${value && target ? ui.goAttr(target) : ""}>${value}</span></td>`;
		const hours = (v, target) => `<td class="pf-hrs">${v && target ? `<span ${ui.goAttr(target)}>${flt(v, 1)} <small>${__("h")}</small></span>` : `${flt(v, 1)} <small>${__("h")}</small>`}</td>`;
		const targets = (project) => ({
			created: wi(project, between("creation")),
			closed: wi(project, { is_closed: 1, ...between("closed_on") }),
			progress: wi(project, { is_closed: 0, status: "In Progress", ...between("creation") }),
			client: wi(project, { is_closed: 0, dependent_on_client: 1, ...between("creation") }),
			billable: te(project, { is_billable: 1, ...between("date") }),
			spent: te(project, between("date")),
		});
		const share = (b, a) => {
			const pct = a ? Math.round((b / a) * 100) : null;
			return `<td>${pct === null ? "<span class='pf-na'>–</span>" : `<span class="pf-mini"><b>${pct}%</b><i style="--w:${pct}%"></i></span>`}</td>`;
		};
		const all_targets = targets(["in", rows.map((r) => r.project)]);
		const notes_cell = (name) => {
			const p = this.data.projects.find((x) => x.name === name);
			return `<td class="pf-notes-cell"><div class="pf-card-foot">${p ? this.note_foot(p) : ""}</div></td>`;
		};
		$body.html(`<table class="table table-sm pf-ttable"><thead><tr><th>${__("Project")}</th><th>${__("Created")}</th><th>${__("Closed")}</th><th>${__("In progress")}</th><th>${__("Waiting on client")}</th><th>${__("Billable time")}</th><th>${__("Actual spent")}</th><th>${__("Billable share")}</th><th>${__("Notes")}</th></tr></thead>
			<tbody>${rows.map((r) => `<tr><td><a class="pf-open" href="/desk/project-hub/${encodeURIComponent(r.project)}/health"><b>${esc(r.project_name)}</b></a> <span class="pf-ident">${esc(r.identifier)}</span></td>${cell(r.created, "pf-tk-created", targets(r.project).created)}${cell(r.closed, "pf-tk-closed", targets(r.project).closed)}${cell(r.in_progress, "pf-tk-prog", targets(r.project).progress)}${cell(r.client_dependent, "pf-tk-client", targets(r.project).client)}${hours(r.billable_hours, targets(r.project).billable)}${hours(r.spent_hours, targets(r.project).spent)}${share(r.billable_hours, r.spent_hours)}${notes_cell(r.project)}</tr>`).join("") || `<tr><td colspan="9" class="text-muted">${__("No projects.")}</td></tr>`}</tbody>
			${rows.length > 1 ? `<tfoot><tr><td><b>${__("Total")}</b> <span class="text-muted small">${__("{0} projects", [rows.length])}</span></td>${cell(total.created, "pf-tk-created", all_targets.created)}${cell(total.closed, "pf-tk-closed", all_targets.closed)}${cell(total.in_progress, "pf-tk-prog", all_targets.progress)}${cell(total.client_dependent, "pf-tk-client", all_targets.client)}${hours(total.billable_hours, all_targets.billable)}${hours(total.spent_hours, all_targets.spent)}${share(total.billable_hours, total.spent_hours)}<td></td></tr></tfoot>` : ""}</table>`);
		ui.bindTiles($body);
		this.bind_notes($body);
	}

	// Trends by project: one smooth line per project; the tabs switch the number, the project names show or hide their line.
	trend_panel() {
		const projects = this.view.projects.filter((p) => p.trend);
		if (!projects.length) return "";
		this.trend = { metric: "open", hidden: new Set() };
		this.trend_colour = {};
		const hues = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#06b6d4", "#8b5cf6", "#ef4444", "#84cc16", "#0ea5e9", "#f97316"];
		projects.forEach((p, i) => (this.trend_colour[p.name] = hues[i % hues.length]));
		const tabs = [["open", __("Open backlog")], ["created", __("Created")], ["resolved", __("Resolved")], ["hours", __("Hours")]];
		return `<div class="pf-sec"><h5>${__("Trends by project")}</h5><span>${__(this.data.bucket === "month" ? "per month" : "per week")} · ${__("hover a point for the numbers, click a project to show or hide it")}</span></div>
			<div class="hub-panel pf-trend ph2-in">
				<div class="pf-trend-tools"><div class="pf-tabs">${tabs.map(([key, label]) => `<span class="${key === "open" ? "active" : ""}" data-metric="${key}">${label}</span>`).join("")}</div>
					<div class="pf-legend">${projects.map((p) => `<span data-project="${ui.esc(p.name)}" style="--c:${this.trend_colour[p.name]}"><i></i>${ui.esc(p.project_name)}</span>`).join("")}</div></div>
				<div class="pf-trend-wrap"><div class="pf-trend-svg"></div><div class="pf-trend-tip"></div></div></div>`;
	}

	bind_trend() {
		if (!this.trend) return;
		const $box = this.$body.find(".pf-trend");
		$box.find(".pf-tabs span").on("click", (e) => {
			this.trend.metric = $(e.currentTarget).data("metric");
			$box.find(".pf-tabs span").each((_i, el) => $(el).toggleClass("active", $(el).data("metric") === this.trend.metric));
			this.draw_trend();
		});
		$box.find(".pf-legend span").on("click", (e) => {
			const name = $(e.currentTarget).data("project");
			const shown = this.view.projects.filter((p) => p.trend && !this.trend.hidden.has(p.name)).length;
			if (this.trend.hidden.has(name)) this.trend.hidden.delete(name);
			else if (shown > 1) this.trend.hidden.add(name); // one line always stays
			$box.find(".pf-legend span").each((_i, el) => $(el).toggleClass("off", this.trend.hidden.has($(el).data("project"))));
			this.draw_trend();
		});
		this.draw_trend();
	}

	draw_trend() {
		const d = this.view;
		const esc = ui.esc;
		const metric = this.trend.metric;
		const lines = d.projects.filter((p) => p.trend && !this.trend.hidden.has(p.name));
		const W = 1000, H = 172, left = 34, right = 52, top = 12, base = 144;
		const n = d.labels.length;
		const x = (i) => left + (n > 1 ? (i / (n - 1)) * (W - left - right) : (W - left - right) / 2);
		const peak = Math.max(1, ...lines.flatMap((p) => p.trend[metric]));
		const step = Math.max(1, Math.ceil(peak / 3 / (peak > 15 ? 5 : 1)) * (peak > 15 ? 5 : 1));
		const max = Math.ceil((peak * 1.1) / step) * step;
		const y = (v) => base - (v / max) * (base - top);
		const smooth = (pts) => {
			let path = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
			for (let i = 0; i < pts.length - 1; i++) {
				const [p0, p1, p2, p3] = [pts[i - 1] || pts[i], pts[i], pts[i + 1], pts[i + 2] || pts[i + 1]];
				const cy = (v) => Math.max(top, Math.min(base, v));
				path += ` C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)} ${cy(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)} ${cy(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
			}
			return path;
		};
		const grid = [];
		for (let v = 0; v <= max; v += step) grid.push(`<line x1="${left}" x2="${W - right}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="pt-grid"/><text x="${left - 8}" y="${(y(v) + 3.5).toFixed(1)}" class="pt-y">${v}</text>`);
		const every = Math.max(1, Math.ceil(n / 9));
		const xlabels = d.labels.map((label, i) => (i % every === 0 || i === n - 1 ? `<text x="${x(i).toFixed(1)}" y="${base + 17}" class="pt-x">${esc(label)}</text>` : "")).join("");
		const defs = lines.map((p) => `<linearGradient id="pt-g-${esc(p.name)}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${this.trend_colour[p.name]}" stop-opacity=".16"/><stop offset="1" stop-color="${this.trend_colour[p.name]}" stop-opacity="0"/></linearGradient>`).join("");
		// end labels: keep them at least 15px apart so equal or close values stay readable
		const label_y = {};
		let floor = -1e9;
		const ordered = lines.slice().sort((a, b) => y(a.trend[metric][n - 1]) - y(b.trend[metric][n - 1]));
		ordered.forEach((p) => {
			floor = Math.max(y(p.trend[metric][n - 1]) + 4, floor + 15);
			label_y[p.name] = floor;
		});
		// a stack of equal values near the axis is lifted back into the chart
		let ceiling = base + 6;
		for (let i = ordered.length - 1; i >= 0; i--) {
			label_y[ordered[i].name] = Math.min(label_y[ordered[i].name], ceiling);
			ceiling = label_y[ordered[i].name] - 15;
		}
		const end_route = (p) =>
			metric === "open" ? ui.go("Work Item", { project: p.name, is_closed: 0 })
			: metric === "created" ? ui.go("Work Item", { project: p.name, creation: [">=", d.starts[0]] })
			: metric === "resolved" ? ui.go("Work Item", { project: p.name, status: "Resolved" })
			: ui.go("Time Entry", { project: p.name, date: [">=", d.starts[0]] });
		const paths = lines.map((p, k) => {
			const values = p.trend[metric];
			const pts = values.map((v, i) => [x(i), y(v)]);
			const colour = this.trend_colour[p.name];
			const last = pts[pts.length - 1];
			return `<g class="pt-line" style="--c:${colour};--d:${k * 120}ms">
				<path d="${smooth(pts)} L${last[0].toFixed(1)} ${base} L${pts[0][0].toFixed(1)} ${base} Z" fill="url(#pt-g-${esc(p.name)})" class="pt-area"/>
				<path d="${smooth(pts)}" class="pt-stroke" pathLength="1"/>
				<circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="3" class="pt-pulse"/><circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="3.2" class="pt-dot"/><circle cx="${(last[0] - 0.9).toFixed(1)}" cy="${(last[1] - 0.9).toFixed(1)}" r="1" class="pt-shine"/>
				<text x="${(last[0] + 10).toFixed(1)}" y="${label_y[p.name].toFixed(1)}" class="pt-end" ${ui.goAttr(end_route(p))}>${flt(values[values.length - 1], 1)}</text></g>`;
		}).join("");
		const $svg = this.$body.find(".pf-trend-svg").html(`<svg viewBox="0 0 ${W} ${H}" class="pt-svg"><defs>${defs}</defs>${grid.join("")}<line x1="${left}" x2="${W - right}" y1="${base}" y2="${base}" class="pt-axis"/>${xlabels}${paths}
			<line class="pt-guide" y1="${top}" y2="${base}" x1="0" x2="0"/><g class="pt-hover"></g><rect x="${left}" y="${top}" width="${W - left - right}" height="${base - top}" fill="transparent" class="pt-hit"/></svg>`);
		ui.bindTiles($svg);
		const $tip = this.$body.find(".pf-trend-tip").removeClass("show");
		const svg = $svg.find("svg")[0];
		$svg.find(".pt-hit").on("mousemove", (e) => {
			const box = svg.getBoundingClientRect();
			const vx = ((e.clientX - box.left) / box.width) * W;
			const i = Math.max(0, Math.min(n - 1, Math.round(((vx - left) / (W - left - right)) * (n - 1))));
			const gx = x(i);
			$svg.find(".pt-guide").attr({ x1: gx, x2: gx }).addClass("show");
			$svg.find(".pt-hover").html(lines.map((p) => `<circle cx="${gx.toFixed(1)}" cy="${y(p.trend[metric][i]).toFixed(1)}" r="3.8" fill="${this.trend_colour[p.name]}" class="pt-point"/>`).join(""));
			$tip.html(`<b>${esc(d.labels[i])}</b>${lines.slice().sort((a, b) => b.trend[metric][i] - a.trend[metric][i]).map((p) => `<span><i style="background:${this.trend_colour[p.name]}"></i>${esc(p.project_name)}<em>${flt(p.trend[metric][i], 1)}</em></span>`).join("")}`)
				.css({ left: `${Math.min(80, Math.max(2, (gx / W) * 100 + (gx / W > 0.6 ? -24 : 3)))}%` }).addClass("show");
		}).on("mouseleave", () => {
			$svg.find(".pt-guide").removeClass("show");
			$svg.find(".pt-hover").empty();
			$tip.removeClass("show");
		});
	}

	// Team capacity: each person's allocation split by project against 100% of their week (projects shown on this page only)
	// ``focus``: the names of the focused projects, or null for all. Only the members of those projects are listed; their
	// whole week still counts, so over-allocation stays visible, and the other projects are shown faded.
	capacity_panel(focus) {
		const c = this.view.capacity;
		if (!c || !c.people.length) return "";
		const esc = ui.esc;
		const hues = ["#6366f1", "#06b6d4", "#f59e0b", "#ec4899", "#8b5cf6", "#14b8a6", "#f97316", "#64748b", "#84cc16", "#0ea5e9"];
		const colour = {};
		const labels = {};
		c.people.forEach((m) =>
			m.projects.filter((p) => p.pct).forEach((p) => {
				labels[p.project] = p.label;
				colour[p.project] = colour[p.project] || hues[Object.keys(colour).length % hues.length];
			})
		);
		const people = focus ? c.people.filter((m) => m.member_of.some((name) => focus.includes(name))) : c.people;
		const over = people.filter((m) => m.over_allocated).length;
		const burnout = people.filter((m) => m.burnout).length;
		const avg = people.length ? Math.round(people.reduce((t, m) => t + m.total_pct, 0) / people.length) : 0;
		const spare = people.reduce((t, m) => t + Math.max(0, 100 - m.total_pct), 0) * c.capacity / 100;
		const span = Math.max(120, ...c.people.map((m) => m.total_pct));
		const state = { over: ["ph2-chip-bad", __("Over-used")], under: ["ph2-chip-warn", __("Under-used")], ok: ["ph2-chip-ok", __("On plan")], none: ["", __("Not allocated")] };
		const h = (v) => `${flt(v, 1)}`;
		const since = frappe.datetime.add_days(frappe.datetime.get_today(), -7 * c.weeks + 1);
		const rows = people.map((m) => `<div class="al-cap-row pf-cap-row" ${ui.goAttr(ui.go("Time Entry", { user: m.user, date: [">=", since] }))}>
			<span class="al-cap-name" title="${esc(m.name)}">${esc(m.name)}</span>
			<div class="al-cap-bar ${m.over_allocated ? "al-cap-over" : ""}">${m.projects.filter((p) => p.pct).map((p) => `<i style="width:${(p.pct / span) * 100}%;background:${colour[p.project]};opacity:${focus && !focus.includes(p.project) ? 0.3 : 1}" title="${esc(p.label)}: ${p.pct}% · ${h(p.logged_week)} h/wk ${__("logged")}"></i>`).join("")}<em style="left:${(100 / span) * 100}%"></em></div>
			<b class="${m.over_allocated ? "ph2-bad" : ""}">${m.total_pct}%</b>
			<small>${__("{0} of {1} h/wk", [h(m.logged_week), h(m.allocated_week)])}</small>
			<span>${m.over_allocated ? `<span class="ph2-chip ph2-chip-bad">${__("Over-allocated")}</span>` : ""}${m.burnout ? `<span class="ph2-chip ph2-chip-bad">${__("Burnout risk")}</span>` : ""}${!m.over_allocated && !m.burnout ? `<span class="ph2-chip ${state[m.state][0]}">${m.utilisation_pct === null ? "" : `${m.utilisation_pct}% · `}${state[m.state][1]}</span>` : ""}</span>
		</div>`);
		return `<div class="hub-panel pf-cap"><h6>${__("Team capacity")}<span class="pf-cap-note">${__("allocation across projects · last {0} weeks · {1} h week", [c.weeks, flt(c.capacity, 0)])}</span>${ui.viewAll(ui.go("Project", { pms_enabled: 1 }))}</h6>
			<div class="pf-cap-sum">
				<div><span>${__("People")}</span><b>${people.length}</b></div>
				<div><span>${__("Average allocation")}</span><b>${avg}%</b></div>
				<div><span>${__("Over-allocated")}</span><b class="${over ? "ph2-bad" : ""}">${over}</b></div>
				<div><span>${__("Burnout risk")}</span><b class="${burnout ? "ph2-bad" : ""}">${burnout}</b></div>
				<div><span>${__("Unallocated time")}</span><b>${h(spare)}<small> ${__("h/wk")}</small></b></div>
			</div>
			<div class="al-cap-keys">${Object.keys(labels).map((p) => `<em><i style="background:${colour[p]}"></i>${esc(labels[p])}</em>`).join("")}<em><i class="pf-cap-mark"></i>${__("100% of the week")}</em></div>
			${rows.join("") || `<div class="text-muted small">${__("These projects have no members yet.")}</div>`}
		</div>`;
	}

	set_filter(key) {
		this.filter = key;
		this.$body.find(".hub-chip").each((_i, el) => $(el).toggleClass("active", $(el).data("filter") === key));
		this.render_table();
		this.render_below();
	}

	render_table() {
		const order = { red: 0, amber: 1, green: 2, none: 3 };
		let rows = this.scoped().rows.slice();
		const { key, asc } = this.sort;
		const value = (p) => (key === "level" ? [order[p.level], p.score === null ? 101 : p.score] : key === "project_name" ? p.project_name.toLowerCase() : flt(p[key]));
		rows = rows.sort((a, b) => {
			const x = value(a);
			const y = value(b);
			const cmp = Array.isArray(x) ? x[0] - y[0] || x[1] - y[1] : x < y ? -1 : x > y ? 1 : 0;
			return asc ? cmp : -cmp;
		});
		const cols = [["project_name", __("Project")], ...(this.show_health ? [["level", __("Health")]] : []), ["open", __("Open")], ["overdue_pct", __("Overdue %")], ["completion_pct", __("Done %")], ["burn_pct", __("Burn %")], ["billable_pct", __("Billable %")], ["client_dependent", __("Client")], ["risks_open", __("Risks")], ["hours_period", __("Hours")]];
		const head = cols.map(([k, label]) => `<th class="${key === k ? `sorted ${asc ? "asc" : ""}` : ""}" data-key="${k}">${label}</th>`).join("");
		const today = frappe.datetime.get_today();
		const lk = (html, target) => `<span class="pf-link" ${ui.goAttr(target)}>${html}</span>`;
		const wi = (p, extra) => ui.go("Work Item", { project: p.name, ...extra });
		const te = (p, extra) => ui.go("Time Entry", { project: p.name, ...extra });
		const mini = (value, tone) => (value === null || value === undefined ? "<span class='pf-na'>–</span>" : `<span class="pf-mini ${tone || ""}"><b>${value}%</b><i style="--w:${Math.min(100, value)}%"></i></span>`);
		const body = rows.length
			? rows.map((p) => `<tr class="hub-clickrow ${this.selected.has(p.name) ? "selected" : ""}" data-project="${ui.esc(p.name)}">
						<td><a class="pf-open" href="/desk/project-hub/${encodeURIComponent(p.name)}/health" title="${__("Open the health report")}"><b>${ui.esc(p.project_name)}</b></a> <span class="pf-ident">${ui.esc(p.identifier)}</span> ${this.note_button(p)}${p.sprint ? `<div class="hub-sub">${ui.esc(p.sprint.label)} · ${flt(p.sprint.percent, 0)}%</div>` : ""}</td>
						${this.show_health ? (p.health_hidden ? "<td><span class='pf-na'>–</span></td>" : `<td title="${ui.esc(p.headline)}"><span class="pf-health pf-${p.level}"><i></i>${ui.esc(p.label)}${p.score === null ? "" : ` <b>${p.score}</b>`}</span></td>`) : ""}
						<td>${lk(`<b>${p.open}</b>`, wi(p, { is_closed: 0 }))}</td><td>${lk(mini(p.overdue_pct, p.overdue_pct > 25 ? "pf-bad" : ""), wi(p, { is_closed: 0, due_date: ["<", today] }))}</td><td>${lk(mini(p.completion_pct), wi(p, { is_closed: 1 }))}</td>
						<td>${lk(mini(p.burn_pct, p.burn_pct > 100 ? "pf-bad" : ""), te(p))}</td><td>${lk(mini(p.billable_pct), te(p, { is_billable: 1 }))}</td>
						<td>${p.client_dependent ? lk(`<span class="pf-tag pf-tag-warn">${p.client_dependent}</span>`, wi(p, { is_closed: 0, dependent_on_client: 1 })) : "<span class='pf-na'>–</span>"}</td>
						<td title="${__("{0} critical, {1} high", [p.risks_critical, p.risks_high])}">${p.risks_open ? lk(`<b>${p.risks_open}</b>${p.risks_critical ? ` <span class="pf-tag pf-tag-bad">${p.risks_critical} ${__("critical")}</span>` : ""}`, ui.go("Risk Register", { project: p.name, status: ["in", ui.OPEN_RISK] })) : "<span class='pf-na'>–</span>"}</td><td>${lk(p.hours_period, te(p, { date: [">=", this.data.range_start] }))}</td></tr>`).join("")
			: `<tr><td colspan="${cols.length}" class="text-muted">${__("No projects match.")}</td></tr>`;
		const $box = this.$body.find(".hub-projects").html(`<table class="table table-sm hub-table sortable pf-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`);
		$box.find("th").on("click", (e) => {
			const k = $(e.currentTarget).data("key");
			this.sort = { key: k, asc: this.sort.key === k ? !this.sort.asc : k === "project_name" || k === "level" };
			this.render_table();
		});
		$box.find(".pf-open").on("click", (e) => e.stopPropagation());
		ui.bindTiles($box);
		this.bind_notes($box);
		$box.find("tr[data-project]").on("click", (e) => {
			const name = $(e.currentTarget).data("project");
			if (this.selected.has(name)) this.selected.delete(name);
			else this.selected.add(name);
			this.render_table();
			this.render_below();
		});
	}
}

auri_pms.Portfolio = Portfolio;
})();
