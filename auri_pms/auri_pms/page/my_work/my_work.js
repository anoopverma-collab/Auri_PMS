// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

/* global auri_pms */
// My Work: my open tickets by due date, what blocks me, my hours this week and my sprints.
let ui; // shared UI kit (auri_hub.bundle.js)

frappe.pages["my-work"].on_page_load = function (wrapper) {
	frappe.require("auri_hub.bundle.js", () => {
		ui = auri_pms.ui;
		wrapper.my_work = new MyWork(wrapper);
		wrapper.my_work.load();
	});
};

frappe.pages["my-work"].on_page_show = function (wrapper) {
	if (wrapper.my_work) wrapper.my_work.load();
};

const MW_GROUPS = [
	["overdue", "Overdue", true],
	["today", "Due today", true],
	["week", "Due this week", true],
	["later", "Later", false],
	["no_due", "No due date", false],
];

const MW_TABS = [
	["today", "Today"],
	["all", "All tickets"],
	["planning", "Planning"],
	["insights", "Insights"],
];

class MyWork {
	constructor(wrapper) {
		const { page, $body } = ui.initPage(wrapper, "My Work");
		this.page = page;
		this.$body = $body;
	}

	load() {
		this.page.clear_inner_toolbar();
		this.page.clear_menu();
		ui.applyTheme(this.$body);
		this.page.add_inner_button(__("Refresh"), () => this.load());
		this.page.add_inner_button(__("Project Hub"), () => frappe.set_route("project-hub"));
		ui.addThemeMenu(this.page, () => this.load());
		this.$body.html(`<div class="text-muted p-4">${__("Loading...")}</div>`);
		frappe.xcall("auri_pms.auri_pms.api.get_my_work").then((data) => {
			this.data = data;
			this.render();
		});
	}

	log_time(name, subject) {
		frappe.prompt(
			[
				{ fieldname: "hours", label: __("Hours"), fieldtype: "Float", reqd: 1 },
				{ fieldname: "activity_type", label: __("Activity"), fieldtype: "Link", options: "Activity Type", reqd: 1 },
				{ fieldname: "is_billable", label: __("Billable"), fieldtype: "Check", default: 1 },
				{ fieldname: "date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
				{ fieldname: "comment", label: __("Comment"), fieldtype: "Small Text" },
			],
			(values) =>
				frappe.xcall("auri_pms.auri_pms.api.log_time", { work_item: name, ...values }).then(() => {
					frappe.show_alert({ message: __("Time logged on {0}", [name]), indicator: "green" });
					this.load();
				}),
			__("Log time: {0}", [subject.length > 60 ? `${subject.slice(0, 57)}...` : subject]),
			__("Log")
		);
	}

	// ---- tabs (Today, All tickets, Planning, Insights); the choice is remembered in this browser
	get_tab() {
		try {
			const t = localStorage.getItem("auri_pms_mywork_tab");
			return MW_TABS.some(([k]) => k === t) ? t : "today";
		} catch (e) {
			return "today";
		}
	}

	set_tab(tab) {
		this.tab = tab;
		try {
			localStorage.setItem("auri_pms_mywork_tab", tab);
		} catch (e) {
			// private mode: the tab still switches for this visit
		}
		this.render();
	}

	// A panel: title, count, a link to the full list, then the body.
	pn(title, count, link, body) {
		return `<div class="tk-panel mw2-panel"><div class="mw2-ph"><b>${title}</b>${count === null ? "" : `<span>${count}</span>`}<span class="tk-grow"></span>${link || ""}</div>${body}</div>`;
	}

	empty(text) {
		return `<div class="mw2-none">${text}</div>`;
	}

	// One dense line per ticket, priority dot, ID, subject, flags and tags, priority, due, log time.
	row(i) {
		const esc = ui.esc;
		const short = (v) => esc(String(v).replace(/^.*?-(?=[^-]+$)/, ""));
		const flags =
			(i.blocked_by.length ? `<span class="tk-tag tk-tag-red" title="${esc(i.blocked_by.join(", "))}">${__("Blocked")}</span>` : "") +
			(cint(i.dependent_on_client) ? `<span class="tk-tag tk-tag-orange" title="${esc(i.client_dependency_note || "")}">${__("Client")}</span>` : "");
		const due = i.days_overdue
			? `<span class="tk-due tk-due-late">${__("{0}d late", [i.days_overdue])}</span>`
			: i.due_date === this.data.today
				? `<span class="tk-due tk-due-today">${__("Today")}</span>`
				: `<span class="tk-due">${i.due_date ? frappe.datetime.str_to_user(i.due_date) : __("No date")}</span>`;
		const p = esc(i.priority || "Normal");
		return `<div class="tk-row">
			<i class="tk-pdot tk-prio-${p}"><i></i></i>
			<span class="tk-id">${ui.link("Work Item", i.name)}</span>
			<span class="tk-subject">${esc(i.subject)}</span>
			${flags}<span class="tk-tag">${esc(i.project_label)}</span>
			${i.release ? `<a class="tk-tag tk-tag-pri" href="/desk/release/${encodeURIComponent(i.release)}">${__("Release")} ${short(i.release)}</a>` : ""}
			${i.sprint ? `<a class="tk-tag tk-tag-pri" href="/desk/sprint/${encodeURIComponent(i.sprint)}">${__("Sprint")} ${short(i.sprint)}</a>` : ""}
			<span class="tk-grow"></span>
			<span class="tk-prio tk-prio-${p}"><i></i>${__(i.priority || "Normal")}</span>${due}
			<button class="tk-log" style="opacity:1" data-log="${esc(i.name)}" data-subject="${esc(i.subject)}">${__("Log time")}</button></div>`;
	}

	// The tab marker sits under the active tab (no motion).
	animate() {
		const $tabs = this.$body.find(".mw2 .mw2-tabs");
		const $on = $tabs.find(".pt-tab.pt-on");
		if ($on.length) $tabs.find(".mw2-ind").css({ left: $on[0].offsetLeft, width: $on[0].offsetWidth });
	}

	group(label, color, rows) {
		return rows.length ? `<div class="tk-group-h"><i class="tk-dot-s ${color}"></i>${label}<span>${rows.length}</span></div>${rows.map((i) => this.row(i)).join("")}` : "";
	}

	render() {
		this.tab = this.tab || this.get_tab();
		const d = this.data;
		const t = d.tiles;
		const mine = (filters) => ui.go("Work Item", { _assign: ["like", `%${frappe.session.user}%`], ...filters });
		const week_end = frappe.datetime.add_days(d.week_start, 6);
		const open_list = {
			overdue: mine({ is_closed: 0, due_date: ["<", d.today] }),
			today: mine({ is_closed: 0, due_date: d.today }),
			week: mine({ is_closed: 0, due_date: ["between", [frappe.datetime.add_days(d.today, 1), week_end]] }),
			later: mine({ is_closed: 0, due_date: [">", week_end] }),
			no_due: mine({ is_closed: 0, due_date: ["is", "not set"] }),
		};
		const all_mine = ui.go("Work Item", { _assign: ["like", `%${frappe.session.user}%`], is_closed: 0 });
		const lk = (html, target) => `<span class="pf-link" ${ui.goAttr(target)}>${html}</span>`;

		// ---- header: greeting and what the day looks like
		const now = new Date();
		const wish = now.getHours() < 12 ? __("Good morning") : now.getHours() < 17 ? __("Good afternoon") : __("Good evening");
		const first = (frappe.user.full_name() || "").split(" ")[0];
		const parts = [];
		if (t.overdue) parts.push(__("{0} overdue", [t.overdue]));
		if (t.today) parts.push(__("{0} due today", [t.today]));
		if (t.week) parts.push(__("{0} due this week", [t.week]));
		const day = !t.open ? __("Nothing is open on your list. Enjoy the quiet.") : __("You have {0} open tickets{1}.", [t.open, parts.length ? `: ${parts.join(", ")}` : ""]);
		const friday = now.getDay() === 5 && now.getHours() >= 16 ? ` ${__("Have a great weekend!")}` : "";
		const hello = `<div class="hub-title ins-title mw2-hello"><h4>${wish}, ${ui.esc(first)}</h4><span class="text-muted">${frappe.datetime.str_to_user(d.today)} · ${day}${friday}</span></div>`;
		const tabs = `<nav class="pt-tabs mw2-tabs"><i class="mw2-ind"></i>${MW_TABS.map(([k, l]) => `<a class="pt-tab ${this.tab === k ? "pt-on" : ""}" href="#" data-tab="${k}">${__(l)}</a>`).join("")}</nav>`;

		// ---- Today: dials, what needs me first, what is coming, my hours, what needs attention
		const week_billable = d.hours.billable.reduce((a, b) => a + b, 0);
		const week_total = week_billable + d.hours.non_billable.reduce((a, b) => a + b, 0);
		const sprint = d.sprints[0];
		const rings = [
			ui.ring(Math.min(100, Math.round(flt(t.capacity_pct))), __("My week"), __("{0} of {1} h logged", [flt(t.hours_week, 1), t.capacity]), t.capacity_pct >= 100 ? "g-green" : t.capacity_pct >= 60 ? "g-teal" : "g-orange", ui.go("Time Entry", { user: frappe.session.user, date: ["between", [d.week_start, week_end]] })),
			ui.ring(t.open ? Math.round(((t.open - t.overdue) / t.open) * 100) : 100, __("On time"), t.open ? __("{0} overdue of {1} open", [t.overdue, t.open]) : __("nothing open"), t.overdue ? "g-orange" : "g-green", open_list.overdue),
			sprint ? ui.ring(Math.round(flt(sprint.percent)), __("Sprint"), `${ui.esc(sprint.label)} · ${__("{0} days left", [sprint.days_left])}`, "g-purple", { route: ["Form", "Sprint", sprint.name], filters: {} }) : "",
			ui.ring(week_total ? Math.round((week_billable / week_total) * 100) : null, __("Billable"), week_total ? __("{0} of {1} h this week", [flt(week_billable, 1), flt(week_total, 1)]) : __("no hours yet"), "g-blue", ui.go("Time Entry", { user: frappe.session.user, is_billable: 1, date: ["between", [d.week_start, week_end]] })),
		].filter(Boolean);
		const missing = d.hours.missing_days.length ? `<div class="mw2-note"><span class="tk-tag tk-tag-orange">${__("No hours logged on {0}", [d.hours.missing_days.join(", ")])}</span></div>` : "";
		const attention = [
			[t.blocked, __("Blocked tickets"), "red", ui.go("Work Item", { name: ["in", Object.values(d.groups).flat().filter((i) => i.blocked_by.length).map((i) => i.name).concat(["-"])] })],
			[t.client_waiting, __("Waiting on the client"), "cyan", mine({ is_closed: 0, dependent_on_client: 1 })],
			[d.impact.blocking.length, __("Others are waiting on me"), "orange", all_mine],
			[d.risks.length, __("Risks I own"), "purple", ui.go("Risk Register", { risk_owner: frappe.session.user })],
		]
			.map(([n, label, tone, target]) => `<div class="mw2-att" ${ui.goAttr(target)}><i class="mw2-badge ${tone}">${n}</i><span>${label}</span><span class="tk-grow"></span><em>›</em></div>`)
			.join("");
		const first_up = this.group(__("Overdue"), "red", d.groups.overdue.slice(0, 5)) + this.group(__("Due today"), "orange", d.groups.today.slice(0, 5));
		const today_tab = `<div class="ph2 ph3"><div class="ph3-gauges" style="--n:${rings.length}">${rings.join("")}</div></div>
			<div class="mw2-grid">
				<div class="mw2-col">
					${this.pn(__("Focus for today"), d.groups.overdue.length + d.groups.today.length, ui.viewAll(open_list.overdue, __("Overdue")), first_up || `<div class="mw2-clear"><b>${t.open ? __("Nothing is overdue or due today.") : __("You are all caught up.")}</b><span>${__("Nice work. Pick the next ticket from All tickets when you are ready.")}</span></div>`)}
					${this.pn(__("Coming up this week"), d.groups.week.length, ui.viewAll(open_list.week), d.groups.week.length ? d.groups.week.slice(0, 6).map((i) => this.row(i)).join("") : this.empty(__("Nothing else is due this week.")))}
				</div>
				<div class="mw2-col">
					${this.pn(__("Hours this week"), null, ui.viewAll(ui.go("Time Entry", { user: frappe.session.user })), `<div class="hub-chart" id="mw-hours"></div>${missing}`)}
					${this.pn(__("Needs your attention"), null, "", `<div class="mw2-atts">${attention}</div>`)}
				</div>
			</div>`;

		// ---- All tickets: everything assigned to me, grouped by due date
		const groups = MW_GROUPS.filter(([key]) => d.groups[key].length)
			.map(([key, label]) => this.group(__(label), { overdue: "red", today: "orange", week: "blue", later: "gray", no_due: "gray" }[key], d.groups[key]))
			.join("");
		const all_tab = this.pn(__("My tickets"), t.open, ui.viewAll(all_mine), groups || this.empty(__("Nothing is assigned to you right now.")));

		// ---- Planning: who waits on me, releases, sprints, projects, risks, client waits
		const im = d.impact;
		const cols = (html, n) => html.replace(/(<table[^>]*>)/, `$1<colgroup>${"<col>".repeat(n)}</colgroup>`);
		const state_chip = (state) => ({
			late: `<span class="hub-badge hub-risk-late">${__("Late")}</span>`,
			tight: `<span class="hub-badge hub-risk-risk">${__("Tight")}</span>`,
			ok: `<span class="hub-badge hub-risk-ok">${__("On track")}</span>`,
		})[state] || "";
		const blocking = im.blocking.length
			? cols(ui.table(im.blocking, [__("My ticket"), __("Overdue"), __("Holding up")], (b) =>
				`<tr><td>${ui.link("Work Item", b.name)}<div class="hub-sub">${ui.esc(b.subject)}</div></td>
				<td style="white-space:nowrap" class="${b.days_overdue ? "text-danger" : ""}">${b.days_overdue ? ui.days(b.days_overdue) : ""}</td>
				<td>${b.blocks.map((w) => `<div>${ui.link("Work Item", w.name)} <span class="hub-sub">${ui.esc(w.assignee_name)}</span></div>`).join("")}</td></tr>`), 3)
			: this.empty(__("None of your tickets is holding up someone else."));
		const releases = im.releases.length
			? cols(ui.table(im.releases, [__("Release"), __("Due"), __("My tickets"), __("Hours owed / available"), ""], (r) =>
				`<tr><td>${ui.link("Release", r.name)}<div class="hub-sub">${ui.esc(r.project)}</div></td>
				<td style="white-space:nowrap">${r.due_date ? frappe.datetime.str_to_user(r.due_date) : ""}<div class="hub-sub">${r.days_left === null ? "" : r.days_left < 0 ? __("{0} days overdue", [-r.days_left]) : __("{0} days left", [r.days_left])}</div></td>
				<td>${lk(r.open_items, mine({ release: r.name, is_closed: 0 }))}</td><td style="white-space:nowrap">${r.hours_owed} h / ${r.hours_available} h</td><td style="white-space:nowrap">${state_chip(r.state)}</td></tr>`), 5)
			: this.empty(__("None of your open tickets is in an open release."));
		const projects = im.projects.length
			? cols(ui.table(im.projects, [__("Project"), __("Project ends"), __("Open"), __("Overdue"), __("Hours owed")], (p) =>
				`<tr><td>${ui.link("Project", p.name, p.label)}</td>
				<td style="white-space:nowrap">${p.end_date ? frappe.datetime.str_to_user(p.end_date) : ""}<div class="hub-sub">${p.days_left === null ? "" : p.days_left < 0 ? __("{0} days overdue", [-p.days_left]) : __("{0} days left", [p.days_left])}</div></td>
				<td>${lk(p.open_items, mine({ project: p.name, is_closed: 0 }))}</td><td class="${p.overdue ? "text-danger" : ""}">${p.overdue ? lk(p.overdue, mine({ project: p.name, is_closed: 0, due_date: ["<", d.today] })) : p.overdue}</td><td>${p.hours_owed} h</td></tr>`), 5)
			: this.empty(__("You are not on any project with open tickets."));
		const sprints = d.sprints.length
			? d.sprints.map((s) => `<div class="mw2-sp"><div class="hub-mini"><span>${ui.link("Sprint", s.name, s.label)}</span><div class="progress"><div class="progress-bar" style="width:${s.percent}%"></div></div><span>${__("{0} days left", [s.days_left])}</span></div>
				<div class="hub-sub">${__("My tickets")}: ${lk(s.mine_closed, mine({ sprint: s.name, is_closed: 1 }))} ${__("of")} ${lk(s.mine_total, mine({ sprint: s.name }))} ${__("closed")}</div></div>`).join("")
			: this.empty(__("No active sprint with your tickets."));
		const waiting_rows = Object.values(d.groups).flat().filter((i) => cint(i.dependent_on_client));
		const waiting = waiting_rows.length
			? ui.table(waiting_rows, [__("Ticket"), __("Summary"), __("What we need"), __("Waiting")], (i) =>
				`<tr><td style="white-space:nowrap">${ui.link("Work Item", i.name)}</td><td>${ui.esc(i.subject)}</td><td>${ui.esc(i.client_dependency_note || "")}</td><td style="white-space:nowrap">${i.client_dependency_since ? ui.days(frappe.datetime.get_diff(d.today, i.client_dependency_since)) : ""}</td></tr>`)
			: this.empty(__("None of your tickets is waiting on the client."));
		const risks = d.risks.length ? ui.riskTable(d.risks, true) : this.empty(__("You do not own any open risks."));
		const planning_tab = `<div class="mw2-grid">
			<div class="mw2-col">
				${this.pn(__("Others are waiting on me"), im.blocking.length, "", `<div class="mw-table mw-blocking mw2-pad">${blocking}</div>`)}
				${this.pn(__("Releases that depend on me"), im.releases.length, ui.viewAll(ui.go("Release", { status: ["!=", "Closed"] })), `<div class="mw-table mw-releases mw2-pad">${releases}</div>`)}
				${this.pn(__("My active sprints"), d.sprints.length, ui.viewAll(ui.go("Sprint", { status: "Active" })), `<div class="mw2-pad">${sprints}</div>`)}
			</div>
			<div class="mw2-col">
				${this.pn(__("Projects I am on"), im.projects.length, ui.viewAll(ui.go("Project", { pms_enabled: 1 })), `<div class="mw-table mw-projects mw2-pad">${projects}</div>`)}
				${this.pn(__("Risks I own"), d.risks.length, ui.viewAll(ui.go("Risk Register", { risk_owner: frappe.session.user })), `<div class="mw2-pad">${risks}</div>`)}
				${this.pn(__("Waiting on the client"), waiting_rows.length, ui.viewAll(mine({ is_closed: 0, dependent_on_client: 1 })), `<div class="mw2-pad">${waiting}</div>`)}
			</div>
		</div>`;

		// ---- Insights: the numbers behind the week and what I closed
		const { tile } = ui;
		const blocked = Object.values(d.groups).flat().filter((i) => i.blocked_by.length).map((i) => i.name);
		const raised = d.raised.length
			? d.raised.map((r) => `<div class="mw2-line"><span>${ui.link("Work Item", r.name)} ${ui.esc(r.subject)}</span><span class="tk-grow"></span><span class="hub-sub">${ui.esc(r.assignee_name)}</span></div>`).join("")
			: this.empty(__("Nothing you raised is waiting on someone else."));
		const insights_tab = `<div class="hub-tiles mw2-tiles">
				${tile(t.open, __("Open tickets"), "hub-blue", "", mine({ is_closed: 0 }))}
				${tile(t.overdue, __("Overdue"), t.overdue ? "hub-red" : "hub-teal", "", mine({ is_closed: 0, due_date: ["<", d.today] }))}
				${tile(t.today, __("Due today"), "hub-orange", "", mine({ is_closed: 0, due_date: d.today }))}
				${tile(t.week, __("Due this week"), "hub-purple", "", mine({ is_closed: 0, due_date: ["between", [d.today, week_end]] }))}
				${tile(t.client_waiting, __("Waiting on client"), "hub-cyan", "", mine({ is_closed: 0, dependent_on_client: 1 }))}
				${tile(t.blocked, __("Blocked"), t.blocked ? "hub-red" : "hub-teal", "", ui.go("Work Item", { name: ["in", blocked.length ? blocked : ["-"]] }))}
				${tile(t.hours_week, __("Hours this week"), "hub-green", __("{0}% of {1} h", [t.capacity_pct, t.capacity]), ui.go("Time Entry", { user: frappe.session.user, date: ["between", [d.week_start, week_end]] }))}
				${tile(t.closed_28d, __("Closed (28 days)"), "hub-teal", "", mine({ is_closed: 1, closed_on: [">=", frappe.datetime.add_days(d.today, -28)] }))}
			</div>
			<div class="mw2-grid">
				<div class="mw2-col">${this.pn(__("Tickets I closed (last 4 weeks)"), null, ui.viewAll(ui.go("Work Item", { closed_by: frappe.session.user, is_closed: 1 })), `<div class="hub-chart mw2-pad" id="mw-closed"></div>`)}</div>
				<div class="mw2-col">${this.pn(__("I raised, others are working on"), d.raised.length, ui.viewAll(ui.go("Work Item", { author: frappe.session.user, is_closed: 0 })), `<div class="mw2-pad">${raised}</div>`)}</div>
			</div>`;

		const body = { today: today_tab, all: all_tab, planning: planning_tab, insights: insights_tab }[this.tab];
		this.$body.html(`<div class="mw tk mw2">${tabs}${hello}<div class="mw2-body">${body}</div></div>`);
		ui.bindTiles(this.$body);
		this.animate();
		this.$body.find("[data-tab]").on("click", (e) => {
			e.preventDefault();
			this.set_tab($(e.currentTarget).attr("data-tab"));
		});
		this.$body.find("[data-log]").on("click", (e) => this.log_time($(e.currentTarget).data("log"), $(e.currentTarget).data("subject")));
		const palette = ui.PALETTE;
		ui.chart(this.$body, "#mw-hours", { type: "bar", height: 200, data: { labels: d.hours.days, datasets: [{ name: __("Billable"), values: d.hours.billable }, { name: __("Non-billable"), values: d.hours.non_billable }] }, colors: [palette.green, palette.orange], barOptions: { stacked: 1, spaceRatio: 0.4 } }, (i) =>
			ui.openTarget(ui.go("Time Entry", { user: frappe.session.user, date: frappe.datetime.add_days(d.week_start, i) }))
		);
		ui.chart(this.$body, "#mw-closed", { type: "bar", height: 200, data: { labels: [__("3 weeks ago"), __("2 weeks ago"), __("Last week"), __("This week")], datasets: [{ name: __("Closed"), values: d.closed_weekly }] }, colors: [palette.purple], barOptions: { spaceRatio: 0.5 } }, (i) => {
			const start = frappe.datetime.add_days(d.week_start, -7 * (3 - i));
			ui.openTarget(ui.go("Work Item", { closed_by: frappe.session.user, is_closed: 1, closed_on: ["between", [start, frappe.datetime.add_days(start, 6)]] }));
		});
	}
}
