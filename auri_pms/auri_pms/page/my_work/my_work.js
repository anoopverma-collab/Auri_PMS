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

	// One compact line per ticket: priority dot, ID and subject, project, due chip, a flag when blocked or waiting, log time.
	ticket_rows(rows) {
		const esc = ui.esc;
		const dot = { Immediate: "red", Urgent: "red", High: "orange", Normal: "blue", Low: "grey" };
		const head = `<div class="mw-row mw-head"><span></span><span>${__("Ticket")}</span><span>${__("Alert")}</span><span class="mw-due">${__("Due")}</span><span></span></div>`;
		return `<div class="mw-list">${head}${rows
			.map((i) => {
				const flag = i.blocked_by.length
					? `<span class="mw-flag mw-flag-bad" title="${esc(i.blocked_by.join(", "))}">${__("Blocked")}</span>`
					: cint(i.dependent_on_client)
						? `<span class="mw-flag mw-flag-warn" title="${esc(i.client_dependency_note || "")}">${__("Client")}</span>`
						: "<span></span>";
				const due = i.days_overdue
					? `<span class="mw-due mw-due-late">${__("{0}d late", [i.days_overdue])}</span>`
					: i.due_date === this.data.today
						? `<span class="mw-due mw-due-today">${__("Today")}</span>`
						: `<span class="mw-due">${i.due_date ? frappe.datetime.str_to_user(i.due_date) : ""}</span>`;
				return `<div class="mw-row">
					<i class="mw-dot mw-dot-${dot[i.priority] || "blue"}" title="${esc(__(i.priority))}"></i>
					<div class="mw-text"><span>${ui.link("Work Item", i.name)}</span> ${esc(i.subject)}<em>${esc(i.project_label)}</em></div>
					${flag}${due}
					<button class="hub-btn" data-log="${esc(i.name)}" data-subject="${esc(i.subject)}">${__("Log time")}</button></div>`;
			})
			.join("")}</div>`;
	}

	render() {
		const d = this.data;
		const t = d.tiles;
		const { tile, panel } = ui;
		const mine = (filters) => ui.go("Work Item", { assigned_to: frappe.session.user, ...filters });
		const week_end = frappe.datetime.add_days(d.week_start, 6);
		const blocked = Object.values(d.groups).flat().filter((i) => i.blocked_by.length).map((i) => i.name);
		const groups = MW_GROUPS.filter(([key]) => d.groups[key].length)
			.map(
				([key, label]) =>
					`<details class="hub-group" ${key === "overdue" ? "open" : ""}><summary>${__(label)} (${d.groups[key].length})</summary>${this.ticket_rows(d.groups[key])}</details>`
			)
			.join("");
		const sprints = d.sprints.length
			? d.sprints
					.map(
						(s) => `<div class="hub-mini"><span>${ui.link("Sprint", s.name, s.label)}</span><div class="progress"><div class="progress-bar" style="width:${s.percent}%"></div></div><span>${__("{0} days left", [s.days_left])}</span></div>
						<div class="hub-sub" style="margin:-4px 0 8px">${__("My tickets: {0} of {1} closed", [s.mine_closed, s.mine_total])}</div>`
					)
					.join("")
			: `<div class="text-muted small">${__("No active sprint with your tickets.")}</div>`;
		const raised = d.raised.length
			? d.raised.map((r) => `<div class="hub-list-row"><span>${ui.link("Work Item", r.name)} ${ui.esc(r.subject)}</span><span class="hub-sub">${ui.esc(r.assignee_name)}</span></div>`).join("")
			: `<div class="text-muted small">${__("Nothing you raised is waiting on someone else.")}</div>`;
		const mine_waiting = Object.values(d.groups).flat().filter((i) => cint(i.dependent_on_client));
		const waiting = mine_waiting.length
			? ui.table(mine_waiting, [__("Ticket"), __("Summary"), __("What we need"), __("Waiting")], (i) =>
				`<tr><td style="white-space:nowrap">${ui.link("Work Item", i.name)}</td><td>${ui.esc(i.subject)}</td><td>${ui.esc(i.client_dependency_note || "")}</td><td style="white-space:nowrap">${i.client_dependency_since ? ui.days(frappe.datetime.get_diff(d.today, i.client_dependency_since)) : ""}</td></tr>`)
			: `<div class="text-muted small">${__("None of your tickets is waiting on the client.")}</div>`;
		const im = d.impact;
		// fixed-width columns (widths live in the bundle's .mw-* rules)
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
			: `<div class="text-muted small">${__("None of your tickets is holding up someone else.")}</div>`;
		const releases = im.releases.length
			? cols(ui.table(im.releases, [__("Release"), __("Due"), __("My tickets"), __("Hours owed / available"), ""], (r) =>
				`<tr><td>${ui.link("Release", r.name)}<div class="hub-sub">${ui.esc(r.project)}</div></td>
				<td style="white-space:nowrap">${r.due_date ? frappe.datetime.str_to_user(r.due_date) : ""}<div class="hub-sub">${r.days_left === null ? "" : r.days_left < 0 ? __("{0} days overdue", [-r.days_left]) : __("{0} days left", [r.days_left])}</div></td>
				<td>${r.open_items}</td><td style="white-space:nowrap">${r.hours_owed} h / ${r.hours_available} h</td><td style="white-space:nowrap">${state_chip(r.state)}</td></tr>`), 5)
			: `<div class="text-muted small">${__("None of your open tickets is in an open release.")}</div>`;
		const projects = im.projects.length
			? cols(ui.table(im.projects, [__("Project"), __("Project ends"), __("Open"), __("Overdue"), __("Hours owed")], (p) =>
				`<tr><td>${ui.link("Project", p.name, p.label)}</td>
				<td style="white-space:nowrap">${p.end_date ? frappe.datetime.str_to_user(p.end_date) : ""}<div class="hub-sub">${p.days_left === null ? "" : p.days_left < 0 ? __("{0} days overdue", [-p.days_left]) : __("{0} days left", [p.days_left])}</div></td>
				<td>${p.open_items}</td><td class="${p.overdue ? "text-danger" : ""}">${p.overdue}</td><td>${p.hours_owed} h</td></tr>`), 5)
			: "";
		const missing = d.hours.missing_days.length ? `<div class="hub-badge hub-badge-warn" style="display:inline-block;margin-top:8px">${__("No hours logged on {0}", [d.hours.missing_days.join(", ")])}</div>` : "";
		this.$body.html(`
			<div class="hub-title"><h4>${__("My Work")}</h4><span class="text-muted">${ui.esc(frappe.user.full_name())} · ${frappe.datetime.str_to_user(d.today)}</span></div>
			<div class="hub-tiles">
				${tile(t.open, __("Open tickets"), "hub-blue", "", mine({ is_closed: 0 }))}
				${tile(t.overdue, __("Overdue"), t.overdue ? "hub-red" : "hub-teal", "", mine({ is_closed: 0, due_date: ["<", d.today] }))}
				${tile(t.today, __("Due today"), "hub-orange", "", mine({ is_closed: 0, due_date: d.today }))}
				${tile(t.week, __("Due this week"), "hub-purple", "", mine({ is_closed: 0, due_date: ["between", [d.today, week_end]] }))}
				${tile(t.client_waiting, __("Waiting on client"), "hub-cyan", "", mine({ is_closed: 0, dependent_on_client: 1 }))}
				${tile(t.blocked, __("Blocked"), t.blocked ? "hub-red" : "hub-teal", "", ui.go("Work Item", { name: ["in", blocked.length ? blocked : ["-"]] }))}
				${tile(t.hours_week, __("Hours this week"), "hub-green", __("{0}% of {1} h", [t.capacity_pct, t.capacity]), ui.go("Time Entry", { user: frappe.session.user, date: ["between", [d.week_start, week_end]] }))}
				${tile(t.closed_28d, __("Closed (28 days)"), "hub-teal", "", mine({ is_closed: 1, closed_on: [">=", frappe.datetime.add_days(d.today, -28)] }))}
			</div>
			<div class="hub-row hub-row-even">
				${panel(`${__("Others are waiting on me")} (${im.blocking.length})`, `<div class="mw-table mw-blocking">${blocking}</div>`)}
				${projects ? panel(__("Projects I am on"), `<div class="mw-table mw-projects">${projects}</div>`) : ""}
			</div>
			<div class="hub-row hub-row-one">${panel(__("Releases that depend on me"), `<div class="mw-table mw-releases">${releases}</div>`)}</div>
			<div class="hub-row hub-row-one">${panel(__("My tickets"), groups || `<div class="text-muted small">${__("Nothing is assigned to you right now.")}</div>`)}</div>
			<div class="hub-row hub-row-even">
				${panel(__("Hours this week"), `<div class="hub-chart" id="mw-hours"></div>${missing}`)}
				${panel(`${__("Risks I own")} (${d.risks.length})`, d.risks.length ? ui.riskTable(d.risks, true) : `<div class="text-muted small">${__("You do not own any open risks.")}</div>`)}
			</div>
			<div class="hub-row hub-row-even">
				${panel(`${__("Waiting on the client")} (${mine_waiting.length})`, waiting)}
				${panel(__("My active sprints"), sprints)}
			</div>
			<div class="hub-row hub-row-even">
				${panel(__("I raised, others are working on"), raised)}
				${panel(__("Tickets I closed (last 4 weeks)"), `<div class="hub-chart" id="mw-closed"></div>`)}
			</div>
			`);
		ui.bindTiles(this.$body);
		this.$body.find("[data-log]").on("click", (e) => this.log_time($(e.currentTarget).data("log"), $(e.currentTarget).data("subject")));
		const palette = ui.PALETTE;
		ui.chart(this.$body, "#mw-hours", { type: "bar", height: 200, data: { labels: d.hours.days, datasets: [{ name: __("Billable"), values: d.hours.billable }, { name: __("Non-billable"), values: d.hours.non_billable }] }, colors: [palette.green, palette.orange], barOptions: { stacked: 1, spaceRatio: 0.4 } });
		ui.chart(this.$body, "#mw-closed", { type: "bar", height: 160, data: { labels: [__("3 weeks ago"), __("2 weeks ago"), __("Last week"), __("This week")], datasets: [{ name: __("Closed"), values: d.closed_weekly }] }, colors: [palette.purple], barOptions: { spaceRatio: 0.5 } });
	}
}
